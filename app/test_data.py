import unittest2
from scratch import \
    User, UserType, UserMapper, InMemoryRepository, Session, ContextualValue


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


class DataTests(unittest2.TestCase):
    def test_can_create_and_store_user(self):
        self.fail()

    def test_can_retrieve_user_from_data_store(self):
        self.fail()

    def test_cannot_store_new_user_with_invalid_data(self):
        self.fail()

    def test_cannot_modify_and_store_existing_user_with_bad_values(self):
        self.fail()

    def test_can_modify_and_store_existing_user_with_valid_values(self):
        self.fail()

    def test_can_perform_a_query_with_transformed_values(self):
        self.fail()

    def test_cannot_delete_others_user(self):
        self.fail()

    def test_can_delete_own_user(self):
        self.fail()

    def test_cannot_perform_invalid_update_with_two_different_instances(self):
        self.fail()
