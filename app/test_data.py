import unittest2
from model import User, UserType, Sound, LicenseType, Annotation
from mapping import UserMapper, SoundMapper, AnnotationMapper
from scratch import \
    Session, ContextualValue, BaseRepository, SortOrder, QueryResult, \
    BaseEntity, BaseDescriptor
from errors import PermissionsError, EntityNotFoundError, ImmutableError


class InMemoryRepository(BaseRepository):
    def __init__(self, cls, mapper):
        super().__init__(cls, mapper)
        self._data = {}

    def __len__(self):
        return len(self._data)

    def upsert(self, *updates):
        for query, update in updates:
            storage_updates = self.mapper.transform_updates(update.values())

            try:
                data = next(self.filter(query))
                data.update(**storage_updates)
                # this is an existing document. update it
            except StopIteration:
                # this is a new document.  insert it
                self._data[query.literal_value] = storage_updates

    def filter(
            self,
            query,
            page_size=100,
            page_number=0,
            sort=None,
            total_count=True):

        f = query.to_lambda('item', self.mapper)
        results = list(filter(f, self._data.values()))

        if sort:
            storage_data = self.mapper.storage_data[sort.field]
            storage_name = storage_data.storage_name
            results = sorted(
                results,
                key=lambda x: x[storage_name],
                reverse=sort.order == SortOrder.DESCENDING)

        total_count = len(results) if total_count else None
        start_pos = page_number * page_size
        page = results[start_pos: start_pos + page_size]
        return QueryResult(page, page_number, page_size, total_count)

    def count(self, query):
        return len(tuple(self.filter(query)))


def user1(user_type=None):
    return dict(
        user_name='Hal',
        password='halation',
        email='hal@eta.com',
        user_type=user_type or UserType.HUMAN,
        about_me='Tennis 4 Life')


def user2():
    return dict(
        user_name='Mike',
        password='peemster',
        email='peemster@eta.com',
        user_type=UserType.HUMAN,
        about_me='DMZ 4 Life')


def sound(
        creator,
        info_url=None,
        audio_url=None,
        license_type=None,
        title=None,
        duration_seconds=None):
    return Sound.create(
        creator=creator,
        created_by=creator,
        info_url=info_url or 'https://archive.org/details/Greatest_Speeches_of_the_20th_Century',
        audio_url=audio_url or 'https://archive.org/download/Greatest_Speeches_of_the_20th_Century/AbdicationAddress.ogg',
        license_type=license_type or LicenseType.BY,
        title='Abdication Address - King Edward VIII' if title is None else title,
        duration_seconds=duration_seconds or (6 * 60) + 42
    )


class EntityTests(unittest2.TestCase):
    def test_inheritance_works(self):
        class A(BaseEntity):
            a = BaseDescriptor()

        class B(A):
            b = BaseDescriptor()

        class C(B):
            c = BaseDescriptor()

        self.assertIn('a', A._metafields)
        self.assertEqual(A, A.a.owner_cls)

        self.assertIn('a', B._metafields)
        self.assertIn('b', B._metafields)
        self.assertEqual(B, B.a.owner_cls)
        self.assertEqual(B, B.b.owner_cls)

        self.assertIn('a', C._metafields)
        self.assertIn('b', C._metafields)
        self.assertIn('c', C._metafields)
        self.assertEqual(C, C.a.owner_cls)
        self.assertEqual(C, C.b.owner_cls)
        self.assertEqual(C, C.c.owner_cls)

        self.assertIsNot(C.a, A.a)
        self.assertIsNot(C.a, B.a)
        self.assertIsNot(B.a, A.a)
        self.assertIsNot(C.b, B.b)

    def test_can_create_new_user(self):
        c = User.create(**user1())
        self.assertEqual('Hal', c.user_name)

    def test_computed_values_are_populated(self):
        c = User.create(**user1())
        self.assertIsNotNone(c.date_created)
        self.assertIsNotNone(c.id)

    def test_validation_errors_when_creating_with_invalid_email(self):
        data = user1()
        data['email'] = 'blah'
        self.assertRaises(ValueError, lambda: User.create(**data))

    def test_validation_errors_when_creating_with_invalid_username(self):
        data = user1()
        data['user_name'] = ''
        self.assertRaises(ValueError, lambda: User.create(**data))

    def test_validation_errors_when_creating_with_invalid_password(self):
        data = user1()
        data['password'] = ''
        self.assertRaises(ValueError, lambda: User.create(**data))

    def test_validation_errors_when_creating_with_invalid_usertype(self):
        data = user1()
        data['user_type'] = 'animal'
        self.assertRaises(ValueError, lambda: User.create(**data))

    def test_validation_errors_when_creating_with_bad_about_me(self):
        data = user1()
        data['user_type'] = UserType.FEATUREBOT
        data['about_me'] = ''
        self.assertRaises(ValueError, lambda: User.create(**data))

    def test_validation_errors_when_modifying_user_with_bad_values(self):
        c = User.create(**user1(user_type=UserType.DATASET))
        c.about_me = ContextualValue(c, '')
        self.assertRaises(ValueError, lambda: c.raise_for_errors())

    def test_user_can_see_own_email_address(self):
        c = User.create(**user1())
        self.assertIn('email', c.view(c))

    def test_user_cannot_see_others_email_address(self):
        c = User.create(**user1())
        c2 = User.create(**user2())
        self.assertNotIn('email', c.view(c2))

    def test_cannot_delete_others_user(self):
        c = User.create(**user1())
        c2 = User.create(**user2())

        def f():
            c.deleted = ContextualValue(c2, True)

        self.assertRaises(PermissionsError, f)

    def test_can_delete_own_user(self):
        c = User.create(**user1())
        c.deleted = ContextualValue(c, True)
        self.assertTrue(c.deleted)


class SoundTests(unittest2.TestCase):
    def test_can_create_sound(self):
        user = User.create(**user1())
        snd = sound(user)
        self.assertEqual(snd.created_by, user)

    def test_permission_error_when_creator_is_featurebot(self):
        user = User.create(**user1(user_type=UserType.FEATUREBOT))
        self.assertRaises(PermissionsError, lambda: sound(user))

    def test_permission_error_when_creator_is_aggregator(self):
        user = User.create(**user1(user_type=UserType.AGGREGATOR))
        self.assertRaises(PermissionsError, lambda: sound(user))

    def test_validation_error_when_info_url_is_invalid(self):
        user = User.create(**user1())
        self.assertRaises(ValueError, lambda: sound(user, info_url='blah'))

    def test_validation_error_when_audio_url_is_invalid(self):
        user = User.create(**user1())
        self.assertRaises(
            ValueError, lambda: sound(user, info_url='audio_url'))

    def test_validation_error_when_license_type_is_invalid(self):
        user = User.create(**user1())
        self.assertRaises(
            ValueError, lambda: sound(user, license_type='sometihing'))

    def test_validation_error_when_title_not_provided(self):
        user = User.create(**user1())
        self.assertRaises(
            ValueError, lambda: sound(user, title=''))

    def test_validation_error_when_duration_invalid(self):
        user = User.create(**user1())
        self.assertRaises(
            ValueError, lambda: sound(user, duration_seconds='blah'))


class AnnotationDataTests(unittest2.TestCase):
    def setUp(self):
        self.user_repo = InMemoryRepository(User, UserMapper)
        self.sound_repo = InMemoryRepository(Sound, SoundMapper)
        self.annotation_repo = InMemoryRepository(Annotation, AnnotationMapper)

    def _session(self):
        return Session(self.user_repo, self.sound_repo, self.annotation_repo)

    def test_permissions_error_when_creator_is_aggregator(self):
        with self._session():
            creator = User.create(**user1(user_type=UserType.HUMAN))
            creator_id = creator.id
            aggregator = User.create(**user1(user_type=UserType.AGGREGATOR))
            aggregator_id = aggregator.id

        with self._session() as s:
            creator = s.find_one(User.id == creator_id)
            snd = sound(creator)
            snd_id = snd.id

        with self._session() as s:
            snd = s.find_one(Sound.id == snd_id)
            aggregator = s.find_one(User.id == aggregator_id)
            self.assertRaises(PermissionsError, lambda: Annotation.create(
                creator=aggregator,
                created_by=aggregator,
                sound=snd,
                start_seconds=1,
                duration_seconds=1,
                tags=['drums'],
                data_url=None
            ))

    def test_can_create_computed_field(self):
        with self._session():
            user = User.create(**user1())
            user_id = user.id

        with self._session() as s:
            user = next(s.filter(User.id == user_id))
            snd = sound(user)
            sound_id = snd.id

        with self._session() as s:
            user = next(s.filter(User.id == user_id))
            snd = next(s.filter(Sound.id == sound_id))
            annotation = Annotation.create(
                creator=user,
                created_by=user,
                sound=snd,
                start_seconds=1,
                duration_seconds=1,
                tags=['drums'],
                data_url=None)

        self.assertEqual(2, annotation.end_seconds)

    def test_error_when_setting_computed_field(self):
        with self._session():
            user = User.create(**user1())
            user_id = user.id

        with self._session() as s:
            user = next(s.filter(User.id == user_id))
            snd = sound(user)
            sound_id = snd.id

        with self._session() as s:
            user = next(s.filter(User.id == user_id))
            snd = next(s.filter(Sound.id == sound_id))
            annotation = Annotation.create(
                creator=user,
                created_by=user,
                sound=snd,
                start_seconds=1,
                duration_seconds=1,
                tags=['drums'],
                data_url=None)

        def x():
            annotation.end_seconds = 10

        self.assertRaises(ImmutableError, x)

    def test_can_store_and_retrieve_with_no_data_url(self):
        with self._session():
            user = User.create(**user1())
            user_id = user.id

        with self._session() as s:
            user = next(s.filter(User.id == user_id))
            snd = sound(user)
            sound_id = snd.id

        with self._session() as s:
            user = next(s.filter(User.id == user_id))
            snd = next(s.filter(Sound.id == sound_id))
            annotation = Annotation.create(
                creator=user,
                created_by=user,
                sound=snd,
                start_seconds=1,
                duration_seconds=1,
                tags=['drums'],
                data_url=None)
            annotation_id = annotation.id

        with self._session():
            annotation = next(s.filter(Annotation.id == annotation_id))
            self.assertIsNone(annotation.data_url)


class SoundDataTests(unittest2.TestCase):
    def setUp(self):
        self.user_repo = InMemoryRepository(User, UserMapper)
        self.sound_repo = InMemoryRepository(Sound, SoundMapper)

    def _session(self):
        return Session(self.user_repo, self.sound_repo)

    def test_created_by_stored_as_string(self):
        with self._session():
            user = User.create(**user1())
            user_id = user.id

        with self._session() as s:
            user = next(s.filter(User.id == user_id))
            snd = sound(user)
            sound_id = snd.id

        self.assertIn(sound_id, self.sound_repo._data)
        raw = self.sound_repo._data[sound_id]
        self.assertEqual(user.id, raw['created_by'])

    def test_created_by_retrieved_as_a_partial_user_instance(self):
        with self._session():
            user = User.create(**user1())
            user_id = user.id

        with self._session() as s:
            user = next(s.filter(User.id == user_id))
            snd = sound(user)
            sound_id = snd.id

        with self._session() as s:
            snd = next(s.filter(Sound.id == sound_id))

        self.assertIsInstance(snd.created_by, User)
        self.assertEqual(snd.created_by.id, user_id)

    def test_date_created_matches(self):
        with self._session():
            user = User.create(**user1())
            user_id = user.id

        with self._session() as s:
            user = next(s.filter(User.id == user_id))
            snd = sound(user)
            date_created = snd.date_created
            sound_id = snd.id
        with self._session() as s:
            snd = next(s.filter(Sound.id == sound_id))

        self.assertEqual(date_created, snd.date_created)


class DataTests(unittest2.TestCase):
    def setUp(self):
        self.repo = InMemoryRepository(User, UserMapper)

    def _session(self):
        return Session(self.repo)

    def test_can_create_and_store_user(self):
        with self._session():
            c = User.create(**user1())
            user_id = c.id

        self.assertEqual(1, len(self.repo._data))
        self.assertIn(user_id, self.repo._data)

    def test_can_retrieve_user_from_data_store(self):
        with self._session():
            c = User.create(**user1())
            user_id = c.id

        with self._session() as s:
            c2 = next(s.filter(User.id == user_id))
            self.assertEqual(c2.email, c.email)

    def test_cannot_store_new_user_with_invalid_data(self):
        def f():
            with self._session():
                data = user1()
                data['user_type'] = UserType.FEATUREBOT
                data['about_me'] = ''
                User.create(**data)

        self.assertRaises(ValueError, f)
        self.assertEqual(0, len(self.repo._data))

    def test_cannot_modify_and_store_existing_user_with_bad_values(self):
        with self._session():
            c = User.create(**user1(user_type=UserType.DATASET))
            original_user_type = c.user_type
            original_about_me = c.about_me
            user_id = c.id

        def f():
            with self._session() as s:
                c2 = next(s.filter(User.id == user_id))
                c2.about_me = ''

        self.assertRaises(ValueError, f)

        with self._session() as s:
            c3 = next(s.filter(User.id == user_id))
            self.assertEqual(original_about_me, c3.about_me)
            self.assertEqual(original_user_type, c3.user_type)

    def test_can_modify_and_store_existing_user_with_valid_values(self):
        with self._session():
            c = User.create(**user1())
            user_id = c.id

        with self._session() as s:
            c2 = next(s.filter(User.id == user_id))
            c2.about_me = ContextualValue(c2, 'modified')

        raw_data = self.repo._data[user_id]
        self.assertEqual('modified', raw_data['about_me'])

    def test_can_perform_a_query_with_transformed_values(self):
        with self._session():
            data = user1()
            password = data['password']
            c = User.create(**data)
            user_id = c.id
            hashed_password = c.password

        with self._session() as s:
            query = (User.id == user_id) & (User.password == password)
            c2 = next(s.filter(query))
            self.assertEqual(hashed_password, c2.password)

    def test_reference_equality_when_fetching_same_entities_in_session(self):
        with self._session():
            c = User.create(**user1())
            user_id = c.id

        with self._session() as s:
            query = (User.id == user_id)
            c2 = next(s.filter(query))
            c3 = next(s.filter(query))
            self.assertIs(c2, c3)
