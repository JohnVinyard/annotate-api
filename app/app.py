import falcon
from model import User, ContextualValue, Sound, Annotation, UserType, \
    LicenseType
from httphelper import \
    decode_auth_header, SessionMiddleware, EntityLinks, CorsMiddleware, \
    exclude_from_docs, encode_query_parameters
from customjson import JSONHandler
from errors import \
    PermissionsError, CompositeValidationError, EntityNotFoundError

USER_URI_TEMPLATE = '/users/{user_id}'
SOUND_URI_TEMPLATE = '/sounds/{sound_id}'

ENTITIES_AS_LINKS = {
    User: USER_URI_TEMPLATE,
    Sound: SOUND_URI_TEMPLATE
}


class AppEntityLinks(EntityLinks):
    def __init__(self):
        super().__init__(ENTITIES_AS_LINKS)


def basic_auth(req, resp, resource, params):
    auth = req.get_header('Authorization')
    if auth is None:
        raise falcon.HTTPUnauthorized()

    try:
        username, password = decode_auth_header(auth)
    except TypeError:
        raise falcon.HTTPUnauthorized()

    session = params['session']
    query = User.auth_query(username, password)

    try:
        user = session.find_one(query)
        req.context['actor'] = user
        params['actor'] = user
    except EntityNotFoundError:
        raise falcon.HTTPUnauthorized()


class RootResource(object):
    def __init__(
            self, user_repo, sound_repo, annotation_repo, is_dev_environment):
        self.is_dev_environment = is_dev_environment
        self.annotation_repo = annotation_repo
        self.sound_repo = sound_repo
        self.user_repo = user_repo
        super().__init__()

    def _get_model(self, total_sounds, total_annotations, total_users):
        return {
            'totalSounds': total_sounds,
            'totalAnnotations': total_annotations,
            'totalUsers': total_users,
        }

    def get_model_example(self, content_type):
        view = self._get_model(
            total_sounds=100, total_annotations=1000, total_users=3)
        return JSONHandler(AppEntityLinks()) \
            .serialize(view, content_type).decode()

    def on_get(self, req, resp, session):
        """
        description:
            Return some high-level stats about users, sounds and annotations
        responses:
            - status_code: 200
              example:
                python: get_model_example
              description: Successfully fetched stats
        """
        resp.media = self._get_model(
            total_sounds=session.count(Sound.all_query()),
            total_annotations=session.count(Annotation.all_query()),
            total_users=session.count(User.all_query()),
        )
        resp.status = falcon.HTTP_200

    @exclude_from_docs
    def on_delete(self, req, resp, session):
        if not self.is_dev_environment:
            raise falcon.HTTPMethodNotAllowed()

        self.user_repo.delete_all()
        self.sound_repo.delete_all()
        self.annotation_repo.delete_all()
        resp.status = falcon.HTTP_NO_CONTENT


def composite_validation_error(e, req, resp, params):
    desc = [(err[0], err[1].args[0]) for err in e.args]
    raise falcon.HTTPBadRequest(description=desc)


def not_found_error(e, req, resp, params):
    raise falcon.HTTPNotFound()


def build_list_response(
        actor,
        items,
        total_count,
        add_next_page,
        link_template,
        **query_parameters):
    views = [item.view(actor) for item in items]
    result = dict(items=views, total_count=total_count)
    if add_next_page:
        encoded_params = encode_query_parameters(**query_parameters)
        result['next'] = link_template.format(encoded_params=encoded_params)
    return result


def list_entity(
        req,
        resp,
        session,
        actor,
        query,
        result_order,
        link_template,
        additional_params=None):
    page_size = req.get_param_as_int('page_size') or 100
    page_number = req.get_param_as_int('page_number') or 0

    page_size_min = 1
    page_size_max = 500

    if page_size < page_size_min or page_size > page_size_max:
        raise falcon.HTTPBadRequest(
            f'Page size must be between '
            f'{page_size_min} and {page_size_max}')

    additional_params = additional_params or {}
    low_id = req.get_param('low_id')
    if low_id is not None:
        query = query & (query.entity_class.id > low_id)
        additional_params['low_id'] = low_id

    query_result = session.filter(
        query,
        page_size,
        page_number,
        result_order)

    results = build_list_response(
        actor=actor,
        items=query_result.results,
        total_count=query_result.total_count,
        add_next_page=query_result.next_page is not None,
        link_template=link_template,
        page_size=page_size,
        page_number=query_result.next_page,
        **additional_params)

    resp.media = results
    resp.status = falcon.HTTP_OK


class SoundsResource(object):
    def get_example_post_body(self):
        return dict(
            info_url='https://archive.org/details/Greatest_Speeches_of_the_20th_Century',
            audio_url='https://archive.org/download/Greatest_Speeches_of_the_20th_Century/AbdicationAddress.ogg',
            license_type='https://creativecommons.org/licenses/by/4.0',
            title='Abdication Address - King Edward VIII',
            duration_seconds=(6 * 60) + 42,
            tags=['speech'])

    @falcon.before(basic_auth)
    def on_post(self, req, resp, session, actor):
        """
        description:
            Create a new sound
        example_request_body:
            python: get_example_post_body
        responses:
            - status_code: 201
              description: Successful sound creation
            - status_code: 400
              description: Input model validation error
            - status_code: 401
              description: Unauthorized request
            - status_code: 403
              description: User is not permitted to create sounds
        """
        data = req.media
        data['created_by'] = actor
        sound = Sound.create(creator=actor, **data)
        resp.set_header('Location', f'/sounds/{sound.id}')
        resp.status = falcon.HTTP_CREATED

    LINK_TEMPLATE = '/sounds?{encoded_params}'

    def get_example_list_model(self, content_type):
        user = User.create(
            user_name='HalIncandenza',
            password='Halation',
            email='hal@enfield.com',
            user_type=UserType.HUMAN,
            about_me='Tennis 4 Life')

        results = build_list_response(
            actor=user,
            items=[
                Sound.create(
                    creator=user,
                    created_by=user,
                    info_url='https://example.com/sound1',
                    audio_url='https://example.com/sound1/file.wav',
                    license_type=LicenseType.BY,
                    title='First sound',
                    duration_seconds=12.3,
                    tags=['test']),
                Sound.create(
                    creator=user,
                    created_by=user,
                    info_url='https://example.com/sound2',
                    audio_url='https://example.com/sound2/file.wav',
                    license_type=LicenseType.BY,
                    title='Second sound',
                    duration_seconds=1.3,
                    tags=['test']),
                Sound.create(
                    creator=user,
                    created_by=user,
                    info_url='https://example.com/sound3',
                    audio_url='https://example.com/sound3/file.wav',
                    license_type=LicenseType.BY,
                    title='Third sound',
                    duration_seconds=30.4,
                    tags=['test']),
            ],
            total_count=100,
            add_next_page=True,
            link_template=SoundsResource.LINK_TEMPLATE,
            page_number=2,
            page_size=3)

        return JSONHandler(AppEntityLinks()) \
            .serialize(results, content_type).decode()

    @falcon.before(basic_auth)
    def on_get(self, req, resp, session, actor):
        """
        description:
            Get a list of sounds
        query_params:
            page_size: The number of results per page
            page_number: The page of results to view
            low_id: Only return identifiers occurring later in the series than
                this one
            created_by: Only return sounds created by the user with this id
        responses:
            - status_code: 200
              description: Successfully fetched a list of sounds
              example:
                python: get_example_list_model
            - status_code: 401
              description: Unauthorized request
            - status_code: 403
              description: User is not permitted to access this sound
        """
        created_by_key = Sound.created_by.name

        user_id = req.get_param(created_by_key)
        additional_params = {}

        if user_id:
            query = Sound.created_by == User.partial_hydrate(id=user_id)
            additional_params[created_by_key] = user_id
        else:
            query = Sound.all_query()

        list_entity(
            req,
            resp,
            session,
            actor,
            query,
            Sound.date_created.ascending(),
            SoundsResource.LINK_TEMPLATE,
            additional_params=additional_params)


def view_entity(session, actor, query):
    # TODO: There should be an option to exclude the total count here
    entity = session.find_one(query)
    view = entity.view(actor)
    return view


def get_entity(resp, session, actor, query):
    view = view_entity(session, actor, query)
    resp.media = view
    resp.status = falcon.HTTP_OK


def head_entity(resp, session, query):
    count = session.count(query)
    if count != 1:
        raise falcon.HTTPNotFound()
    resp.status = falcon.HTTP_NO_CONTENT


class AnnotationsResource(object):
    LINK_TEMPLATE = '/annotations?{encoded_params}'

    def get_example_list_model(self, content_type):
        dataset = User.create(
            user_name='HalIncandenza',
            password='Halation',
            email='hal@enfield.com',
            user_type=UserType.DATASET,
            about_me='Tennis 4 Life')

        snd = Sound.create(
            creator=dataset,
            created_by=dataset,
            info_url='https://example.com/sound1',
            audio_url='https://example.com/sound1/file.wav',
            license_type=LicenseType.BY,
            title='First sound',
            duration_seconds=12.3,
            tags=['test'])

        snd2 = Sound.create(
            creator=dataset,
            created_by=dataset,
            info_url='https://example.com/sound2',
            audio_url='https://example.com/sound2/file.wav',
            license_type=LicenseType.BY,
            title='Second sound',
            duration_seconds=3.2,
            tags=['test'])

        annotations = [
            Annotation.create(
                creator=dataset,
                created_by=dataset,
                sound=snd,
                start_seconds=1,
                duration_seconds=1,
                tags=['snare']
            ),
            Annotation.create(
                creator=dataset,
                created_by=dataset,
                sound=snd,
                start_seconds=2,
                duration_seconds=1,
                tags=['snare']
            ),
            Annotation.create(
                creator=dataset,
                created_by=dataset,
                sound=snd2,
                start_seconds=10,
                duration_seconds=5,
                tags=['snare']
            ),
        ]
        results = build_list_response(
            actor=dataset,
            items=annotations,
            total_count=100,
            add_next_page=True,
            link_template=self.LINK_TEMPLATE,
            page_size=3,
            page_number=2,
            tags='snare')

        return JSONHandler(AppEntityLinks()) \
            .serialize(results, content_type).decode()

    @falcon.before(basic_auth)
    def on_get(self, req, resp, session, actor):
        """
        description:
            Get a list of annotations
        query_params:
            page_size: The number of results per page
            page_number: The page of results to view
            low_id: Only return identifiers occurring later in the series than
                this one
            tags: Only return annotations with all specified tags
        responses:
            - status_code: 200
              description: Successfully fetched an annotation
              example:
                python: get_example_list_model
            - status_code: 401
              description: Unauthorized request
            - status_code: 403
              description: User is not permitted to access this annotation
        """
        query = Annotation.all_query()

        # TODO: This is near-duplicate code from the /sounds resource below.
        # factor it out
        additional_params = {}
        tags = req.get_param_as_list('tags')
        if tags:
            additional_params['tags'] = tags
            for tag in tags:
                query = query & (Annotation.tags == tag)

        list_entity(
            req,
            resp,
            session,
            actor,
            query,
            Annotation.date_created.ascending(),
            self.LINK_TEMPLATE,
            additional_params=additional_params)


class SoundAnnotationsResource(object):
    def get_example_post_body(self):
        return dict(
            start_seconds=1.2,
            duration_seconds=0.5,
            tags=['snare', 'hi-hat'],
            data_url='https://s3/data/numpy-fft-feature.dat')

    @falcon.before(basic_auth)
    def on_post(self, req, resp, sound_id, session, actor):
        """
        description:
            Create a new annotation for the sound with identifier `sound_id`.
            Text tags can be added directly to the resource via the `tags`
            field, or arbitrary binary or other structured data may be pointed
            to via the `data_url` parameter.
        url_params:
            sound_id: The identifier of the sound to annotate
        example_request_body:
            python: get_example_post_body
        responses:
            - status_code: 201
              description: Successful annotation creation
            - status_code: 400
              description: Input model validation error
            - status_code: 404
              description: Provided an invalid `sound_id`
            - status_code: 401
              description: Unauthorized request
            - status_code: 403
              description: User is not permitted to create annotations
        """
        sound = session.find_one(Sound.id == sound_id)

        for annotation in req.media['annotations']:
            annotation['created_by'] = actor
            annotation['sound'] = sound
            Annotation.create(
                creator=actor,
                **annotation)
        resp.set_header('Location', f'/sounds/{sound_id}/annotations')
        resp.status = falcon.HTTP_CREATED

    def link_template(self, sound_id):
        return f'/sounds/{sound_id}/annotations?{{encoded_params}}'

    def get_example_list_model(self, content_type):
        dataset = User.create(
            user_name='HalIncandenza',
            password='Halation',
            email='hal@enfield.com',
            user_type=UserType.DATASET,
            about_me='Tennis 4 Life')

        featurebot = User.create(
            user_name='FFTBot',
            password='password',
            email='fftbot@gmail.com',
            user_type=UserType.FEATUREBOT,
            about_me='I compute FFT features')

        snd = Sound.create(
            creator=dataset,
            created_by=dataset,
            info_url='https://example.com/sound',
            audio_url='https://example.com/sound/file.wav',
            license_type=LicenseType.BY,
            title='A sound',
            duration_seconds=12.3,
            tags=['test'])

        annotations = [
            Annotation.create(
                creator=dataset,
                created_by=dataset,
                sound=snd,
                start_seconds=1,
                duration_seconds=1,
                tags=['kick']
            ),
            Annotation.create(
                creator=dataset,
                created_by=dataset,
                sound=snd,
                start_seconds=2,
                duration_seconds=1,
                tags=['snare']
            ),
            Annotation.create(
                creator=featurebot,
                created_by=featurebot,
                sound=snd,
                start_seconds=0,
                duration_seconds=12.3,
                data_url='https://s3/fft-data/file.dat'
            )
        ]
        results = build_list_response(
            actor=dataset,
            items=annotations,
            total_count=100,
            add_next_page=True,
            link_template=self.link_template(snd.id),
            page_size=3,
            page_number=2)
        return JSONHandler(AppEntityLinks()) \
            .serialize(results, content_type).decode()

    @falcon.before(basic_auth)
    def on_get(self, req, resp, sound_id, session, actor):
        """
        description:
            Get a list of annotations for the sound with id `sound_id`
        url_params:
            sound_id: The sound to list annotations for
        query_params:
            page_size: The number of results per page
            page_number: The page of results to view
            low_id: Only return identifiers occurring later in the series than
                this one
            time_range: Only return annotations overlapping with the specified
                time range
        responses:
            - status_code: 200
              description: Successfully fetched a list of annotations
              example:
                python: get_example_list_model
            - status_code: 404
              description: Provided an unknown sound identifier
            - status_code: 401
              description: Unauthorized request
            - status_code: 403
              description: User is not permitted to access annotations for
                this sound
        """
        sound = session.find_one(Sound.id == sound_id)
        query = Annotation.sound == sound

        additional_params = {}
        time_range = req.get_param('time_range')

        if time_range is not None:
            try:
                start, end = time_range.split('-')
                start = float(start)
                end = float(end)
                not_intersects_query = \
                    (Annotation.start_seconds > end) \
                    | (Annotation.end_seconds < start)
                query = query & not_intersects_query.negate()
                additional_params['time_range'] = time_range
            except ValueError:
                raise falcon.HTTPBadRequest(
                    'Please specify time ranges as two '
                    'dash-separated float values')

        created_by = req.get_param('created_by')
        if created_by is not None:
            partial_user = User.partial_hydrate(id=created_by)
            user_query = (Annotation.created_by == partial_user)
            query = query & user_query
            additional_params['created_by'] = created_by

        list_entity(
            req,
            resp,
            session,
            actor,
            query,
            Annotation.date_created.ascending(),
            self.link_template(sound_id),
            additional_params=additional_params)


class UserSoundsResource(object):
    def link_template(self, user_id):
        return f'/users/{user_id}/sounds?{{encoded_params}}'

    def get_example_list_model(self, content_type):
        user = User.create(
            user_name='HalIncandenza',
            password='Halation',
            email='hal@enfield.com',
            user_type=UserType.HUMAN,
            about_me='Tennis 4 Life')

        results = build_list_response(
            actor=user,
            items=[
                Sound.create(
                    creator=user,
                    created_by=user,
                    info_url='https://example.com/sound1',
                    audio_url='https://example.com/sound1/file.wav',
                    license_type=LicenseType.BY,
                    title='First sound',
                    duration_seconds=12.3,
                    tags=['test']),
                Sound.create(
                    creator=user,
                    created_by=user,
                    info_url='https://example.com/sound2',
                    audio_url='https://example.com/sound2/file.wav',
                    license_type=LicenseType.BY,
                    title='Second sound',
                    duration_seconds=1.3,
                    tags=['test']),
                Sound.create(
                    creator=user,
                    created_by=user,
                    info_url='https://example.com/sound3',
                    audio_url='https://example.com/sound3/file.wav',
                    license_type=LicenseType.BY,
                    title='Third sound',
                    duration_seconds=30.4,
                    tags=['test']),
            ],
            total_count=100,
            add_next_page=True,
            link_template=self.link_template(user.id),
            page_number=2,
            page_size=3)

        return JSONHandler(AppEntityLinks()) \
            .serialize(results, content_type).decode()

    @falcon.before(basic_auth)
    def on_get(self, req, resp, user_id, session, actor):
        """
        description:
            Get a list of sounds belonging to a user with id `user_id`
        url_params:
            user_id: The user who created the sounds
        query_params:
            page_size: The number of results per page
            page_number: The page of results to view
            low_id: Only return identifiers occurring later in the series than
                this one
            tags: Only return sounds with all tags specified
        responses:
            - status_code: 200
              description: Successfully fetched a list of sounds
              example:
                python: get_example_list_model
            - status_code: 404
              description: Provided an unknown user identifier
            - status_code: 401
              description: Unauthorized request
            - status_code: 403
              description: User is not permitted to access sounds from this user
        """
        user = session.find_one(User.id == user_id)
        query = Sound.created_by == user

        additional_params = {}
        tags = req.get_param_as_list('tags')
        if tags:
            additional_params['tags'] = tags
            for tag in tags:
                query = query & (Sound.tags == tag)

        list_entity(
            req,
            resp,
            session,
            actor,
            query,
            Sound.date_created.ascending(),
            self.link_template(user_id),
            additional_params=additional_params)


class UserAnnotationResource(object):
    def link_template(self, user_id):
        return f'/users/{user_id}/annotations?{{encoded_params}}'

    def get_model_example(self, content_type):
        dataset = User.create(
            user_name='HalIncandenza',
            password='Halation',
            email='hal@enfield.com',
            user_type=UserType.DATASET,
            about_me='Tennis 4 Life')

        snd = Sound.create(
            creator=dataset,
            created_by=dataset,
            info_url='https://example.com/sound',
            audio_url='https://example.com/sound/file.wav',
            license_type=LicenseType.BY,
            title='A sound',
            duration_seconds=12.3,
            tags=['test'])

        annotations = [
            Annotation.create(
                creator=dataset,
                created_by=dataset,
                sound=snd,
                start_seconds=1,
                duration_seconds=1,
                tags=['kick']
            ),
            Annotation.create(
                creator=dataset,
                created_by=dataset,
                sound=snd,
                start_seconds=2,
                duration_seconds=1,
                tags=['snare']
            ),
        ]
        results = build_list_response(
            actor=dataset,
            items=annotations,
            total_count=100,
            add_next_page=True,
            link_template=self.link_template(dataset.id),
            page_size=2,
            page_number=2)
        return JSONHandler(AppEntityLinks()) \
            .serialize(results, content_type).decode()

    @falcon.before(basic_auth)
    def on_get(self, req, resp, user_id, session, actor):
        """
        description:
            List annotations created by a user with id `user_id`
        url_params:
            user_id: The user who created the annotations
        query_params:
            page_size: The number of results per page
            page_number: The current page
        responses:
            - status_code: 200
              description: Successfully fetched a list of annotations
              example:
                python: get_model_example
            - status_code: 404
              description: Provided an unknown user identifier
            - status_code: 401
              description: Unauthorized request
            - status_code: 403
              description: User is not permitted to access annotationsfrom
                this user
        """
        user = session.find_one(User.id == user_id)
        query = Annotation.created_by == user

        list_entity(
            req,
            resp,
            session,
            actor,
            query,
            Annotation.date_created.ascending(),
            self.link_template(user_id))


class UsersResource(object):
    def get_example_post_body(self):
        return {
            'user_name': 'HalIncandenza',
            'password': 'password',
            'user_type': UserType.HUMAN.value,
            'email': 'hal@eta.com',
            'about_me': 'Up and coming tennis star',
            'info_url': 'https://hal.eta.net'
        }

    def on_post(self, req, resp, session):
        """
        description:
            Create a new user
        example_request_body:
            python: get_example_post_body
        responses:
            - status_code: 201
              description: Successful user creation
            - status_code: 400
              description: Input model validation error
        """
        user = User.create(**req.media)
        resp.set_header('Location', f'/users/{user.id}')
        resp.status = falcon.HTTP_CREATED

    LINK_TEMPLATE = '/users?{encoded_params}'

    def get_model_example(self, content_type):
        viewer = User.create(
            user_name='HalIncandenza',
            password='password',
            user_type='human',
            email='hal@eta.net',
            about_me='Tennis 4 Life',
            info_url='https://halation.com'
        )

        users = build_list_response(
            viewer,
            [
                viewer,
                User.create(
                    user_name='MikePemulis',
                    password='password',
                    user_type='human',
                    email='peemster@eta.net',
                    about_me='Tennis 4 Life',
                    info_url='https://peemster.com'),
                User.create(
                    user_name='MarioIncandenza',
                    password='password',
                    user_type='human',
                    email='mario@eta.net',
                    about_me='Movies 4 Life',
                    info_url='https://mario.com')
            ],
            200,
            True,
            UsersResource.LINK_TEMPLATE,
            user_type=UserType.HUMAN.value,
            page_size=3,
            page_number=2)
        return JSONHandler(AppEntityLinks()) \
            .serialize(users, content_type).decode()

    @falcon.before(basic_auth)
    def on_get(self, req, resp, session, actor):
        """
        description:
            Get a list of users
        query_params:
            page_size: The number of results per page
            page_number: The page of results to view
            low_id: Only return identifiers occurring later in the series than
                this one
            user_type: Only return users with this type
            user_name: Only return users matching this name
        responses:
            - status_code: 200
              description: Successfully fetched a list of users
              example:
                python: get_model_example
            - status_code: 401
              description: Unauthorized request
            - status_code: 403
              description: User is not permitted to access this sound
        """
        query = User.deleted == False

        additional_params = {}

        user_type = req.get_param(User.user_type.name)
        if user_type:
            try:
                query = (query & (User.user_type == user_type))
            except ValueError as e:
                raise falcon.HTTPBadRequest(e.args[0])
            additional_params[User.user_type.name] = user_type

        user_name = req.get_param(User.user_name.name)
        if user_name is not None:
            query = query & (User.user_name == user_name)
            additional_params[User.user_name.name] = user_name

        list_entity(
            req,
            resp,
            session,
            actor,
            query,
            User.date_created.descending(),
            UsersResource.LINK_TEMPLATE,
            additional_params=additional_params)


class SoundResource(object):
    def get_model_example(self, content_type):
        user = User.create(
            user_name='HalIncandenza',
            password='Halation',
            email='hal@enfield.com',
            user_type=UserType.HUMAN,
            about_me='Tennis 4 Life')
        snd = Sound.create(
            creator=user,
            created_by=user,
            info_url='https://example.com/sound',
            audio_url='https://example.com/sound/file.wav',
            license_type=LicenseType.BY,
            title='A sound',
            duration_seconds=12.3,
            tags=['test'])
        view = snd.view(user)
        return JSONHandler(AppEntityLinks()) \
            .serialize(view, content_type).decode()

    @falcon.before(basic_auth)
    def on_get(self, req, resp, sound_id, session, actor):
        """
        description:
            Fetch an individual sound
        url_params:
            sound_id: The identifier of the sound to fetch
        responses:
            - status_code: 200
              description: Successfully fetched sound
              example:
                python: get_model_example
            - status_code: 404
              description: The sound identifier supplied does not exist
        """

        get_entity(resp, session, actor, Sound.id == sound_id)

    @falcon.before(basic_auth)
    def on_head(self, req, resp, sound_id, session, actor):
        """
        description:
            Check if a sound exists by id
        url_params:
            sound_id: The identifier of the sound to fetch
        responses:
            - status_code: 204
              description: The sound identifier exists
            - status_code: 404
              description: The sound identifier does not exist
        """
        head_entity(resp, session, Sound.id == sound_id)


class UserResource(object):
    def get_model_example(self, content_type):
        user = User.create(
            user_name='HalIncandenza',
            password='Halation',
            email='hal@enfield.com',
            user_type=UserType.HUMAN,
            about_me='Tennis 4 Life')
        view = user.view(user)
        return JSONHandler(AppEntityLinks()) \
            .serialize(view, content_type).decode()

    @falcon.before(basic_auth)
    def on_get(self, req, resp, user_id, session, actor):
        """
        description:
            Fetch an individual user by id.  Some details, such as email, are
            only included when users fetch their own record
        url_params:
            user_id: the identifier of the user to fetch
        responses:
            - status_code: 200
              description: Successfully fetched a user
              example:
                python: get_model_example
            - status_code: 404
              description: Provided an invalid user id
            - status_code: 401
              description: Unauthorized request
            - status_code: 403
              description: User is not permitted to access this user
        """
        get_entity(resp, session, actor, User.active_user_query(user_id))

    @falcon.before(basic_auth)
    def on_head(self, req, resp, user_id, session, actor):
        """
        description:
            Check if a user exists by id
        url_params:
            user_id: check if the user with `user_id` exists
        responses:
            - status_code: 204
              description: The requested user exists
            - status_code: 404
              description: The requested user does not exist
            - status_code: 401
              description: Unauthorized request
            - status_code: 403
              description: User is not permitted to access this user
        """
        head_entity(resp, session, User.active_user_query(user_id))

    @falcon.before(basic_auth)
    def on_delete(self, req, resp, user_id, session, actor):
        """
        description:
            Delete a user with the specified id.  Users may only delete
            themselves.
        url_params:
            user_id: the identifier of the user to delete
        responses:
            - status_code: 200
              description: The user was deleted
            - status_code: 404
              description: The user id does not exist
            - status_code: 401
              description: Unauthorized request
            - status_code: 403
              description: User is not permitted to delete this user
        """
        to_delete = session.find_one(User.id == user_id)
        to_delete.deleted = ContextualValue(actor, True)

    def example_patch_body(self):
        return {
            'about_me': 'Here is some updated about me text',
            'password': 'Here|sANewPa$$w0rd'
        }

    @falcon.before(basic_auth)
    def on_patch(self, req, resp, user_id, session, actor):
        """
        description:
            Update information about the user
        url_params:
            user_id: the identifier of the user to update
        example_request_body:
            python: example_patch_body
        responses:
            - status_code: 204
              description: The user was successfully updated
            - status_code: 400
              description: Input model validation error
            - status_code: 401
              description: Unauthorized request
            - status_code: 403
              description: User is not permitted to update this user
        """
        query = User.active_user_query(user_id)
        to_update = session.find_one(query)
        to_update.update(actor, **req.media)


app_entity_links = AppEntityLinks()


# custom errors
def permissions_error(ex, req, resp, params):
    raise falcon.HTTPForbidden(ex.args[0])


class Application(falcon.API):
    """
    description: |
        Cochlea allows users to annotate audio files on the internet.  Segments
        or time intervals of audio can be annotated with text tags or arbitrary
        structured data hosted on another server.

        Basic Auth is currently the only form of authentication supported.
        Requests for most resources will return a `401 Unauthorized` response if
        the `Authorization` header is missing.

        There are three types of users possible:

        - `dataset` - can create both sounds and annotations, typically
           representing a related group of sounds on the internet, e.g
           [the MusicNet dataset](https://homes.cs.washington.edu/~thickstn/musicnet.html),
           [the NSynth dataset](https://magenta.tensorflow.org/datasets/nsynth),
           or some other collection of sound
        - `featurebot` - an auotmated user that will compute features for
           some or all sounds, e.g., a user that computes short-time fourier
           transforms for each sound and stores the data as serialized numpy
           arrays in an S3 bucket
        - `human` - a human user who is likely to interact with the API via
          a web-based GUI and may create annotations for sounds, likely
          adding textual tags to audio segments
    """

    def __init__(
            self,
            users_repo,
            sounds_repo,
            annotations_repo,
            is_dev_environment):
        super().__init__(middleware=[
            CorsMiddleware(),
            SessionMiddleware(
                app_entity_links, users_repo, sounds_repo, annotations_repo)
        ])

        self._doc_routes = []

        self.req_options.strip_url_path_trailing_slash = True
        self.resp_options.media_handlers = falcon.media.Handlers({
            'application/json': JSONHandler(app_entity_links),
        })
        self.add_route('/', RootResource(
            users_repo, sounds_repo, annotations_repo, is_dev_environment))
        self.add_route('/users', UsersResource())
        self.add_route(USER_URI_TEMPLATE, UserResource())
        self.add_route('/sounds', SoundsResource())
        self.add_route(SOUND_URI_TEMPLATE, SoundResource())
        self.add_route(
            '/sounds/{sound_id}/annotations', SoundAnnotationsResource())
        self.add_route('/users/{user_id}/sounds', UserSoundsResource())
        self.add_route('/users/{user_id}/annotations', UserAnnotationResource())
        self.add_route('/annotations', AnnotationsResource())

        self.add_error_handler(PermissionsError, permissions_error)
        self.add_error_handler(
            CompositeValidationError, composite_validation_error)
        self.add_error_handler(EntityNotFoundError, not_found_error)

    def add_route(self, route, resource, *args, **kwargs):
        self._doc_routes.append((route, resource))
        super().add_route(route, resource, *args, **kwargs)
