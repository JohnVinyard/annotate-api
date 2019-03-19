import unittest2
from scratch import \
    User, UserType, UserMapper, InMemoryRepository, Session, ContextualValue
from errors import PermissionsError


def user1():
    return dict(
        name='Hal',
        password='halation',
        email='hal@eta.com',
        user_type=UserType.HUMAN,
        about_me='Tennis 4 Life')


def user2():
    return dict(
        name='Mike',
        password='peemster',
        email='peemster@eta.com',
        user_type=UserType.HUMAN,
        about_me='DMZ 4 Life')


class EntityTests(unittest2.TestCase):
    def test_can_create_new_user(self):
        c = User.create(**user1())
        self.assertEqual('Hal', c.name)

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
        data['name'] = ''
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
        c = User.create(**user1())
        c.user_type = ContextualValue(c, UserType.FEATUREBOT)
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

        with self._session():
            c2 = next(self.repo.filter(User.id == user_id))
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
            c = User.create(**user1())
            original_user_type = c.user_type
            original_about_me = c.about_me
            user_id = c.id

        def f():
            with self._session():
                c2 = next(self.repo.filter(User.id == user_id))
                c2.user_type = UserType.DATASET
                c2.about_me = ''

        self.assertRaises(ValueError, f)

        with self._session():
            c3 = next(self.repo.filter(User.id == user_id))
            self.assertEqual(original_about_me, c3.about_me)
            self.assertEqual(original_user_type, c3.user_type)

    def test_can_modify_and_store_existing_user_with_valid_values(self):
        with self._session():
            c = User.create(**user1())
            user_id = c.id

        with self._session():
            c2 = next(self.repo.filter(User.id == user_id))
            c2.user_type = ContextualValue(c2, UserType.DATASET)
            c2.about_me = ContextualValue(c2, 'modified')

        raw_data = self.repo._data[user_id]
        self.assertEqual('dataset', raw_data['user_type'])
        self.assertEqual('modified', raw_data['about_me'])

    def test_can_perform_a_query_with_transformed_values(self):
        with self._session():
            data = user1()
            password = data['password']
            c = User.create(**data)
            user_id = c.id
            hashed_password = c.password

        with self._session():
            query = (User.id == user_id) & (User.password == password)
            c2 = next(self.repo.filter(query))
            self.assertEqual(hashed_password, c2.password)

    def test_cannot_perform_invalid_update_with_two_different_instances(self):
        with self._session():
            c = User.create(**user1())
            user_id = c.id
            original_user_type = c.user_type.value
            original_about_me = c.about_me

        def f():
            with self._session():
                c2 = next(self.repo.filter(User.id == user_id))
                c3 = next(self.repo.filter(User.id == user_id))
                c2.user_type = ContextualValue(c2, UserType.FEATUREBOT)
                c3.about_me = ContextualValue(c3, '')

        self.assertRaises(ValueError, f)
        data = self.repo._data[user_id]
        self.assertEqual(original_user_type, data['user_type'])
        self.assertEqual(original_about_me, data['about_me'])
