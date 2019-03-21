import datetime
from password import password_hasher
from identifier import user_id_generator
from errors import PermissionsError
from scratch import UserType, User




# class UserData(object):
#     def __init__(
#             self,
#             _id=None,
#             user_name=None,
#             email=None,
#             user_type=None,
#             about_me=None,
#             date_created=None,
#             deleted=None,
#             **kwargs):
#
#         self.deleted = deleted
#         self.date_created = date_created
#         self.id = _id
#         self.about_me = about_me
#         self.user_type = user_type
#         self.email = email
#         self.user_name = user_name
#
#     @property
#     def is_anonymous(self):
#         return self.id is None
#
#     def create_user(self, **kwargs):
#         if not self.is_anonymous:
#             raise PermissionsError('only anonymous users may create new users')
#         return UserData(**kwargs)
#
#     def delete_user(self, user):
#         if self.id != user.id:
#             raise PermissionsError('You many not delete another user')
#         user.deleted = True
#
#     def view(self, user):
#         data = dict(user.__dict__)
#         del data['deleted']
#
#         if self.id == user.id:
#             return data
#         else:
#             del data['email']
#             return data
#
#
# class UserCreationData(object):
#     def __init__(self, user_name, password, email, user_type, about_me):
#         self.id = user_id_generator()
#         self.password = password_hasher(password)
#         self.date_created = datetime.datetime.utcnow()
#         self.deleted = False
#
#         self.about_me = about_me
#         self.user_name = user_name
#         self.email = email
#         self.user_type = user_type
#
#
# class UserUpdateData(object):
#     def __init__(self, password=None, about_me=None):
#         self.about_me = about_me
#         self.password = password
