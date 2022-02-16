"""OpenVidu class."""
from typing import List, Union, Optional
from functools import partial

from requests_toolbelt.sessions import BaseUrlSession
from requests.auth import HTTPBasicAuth
from requests_toolbelt import user_agent

from . import __version__
from .exceptions import OpenViduSessionDoesNotExistsError, OpenViduSessionExistsError
from .exceptions import OpenViduRecordingDoesNotExistsError
from .openvidusession import OpenViduSession
from .openvidurecording import OpenViduRecording


class OpenVidu(object):
    """
    This object represents a OpenVidu server instance.
    """

    def __init__(
        self,
        url: str,
        secret: str,
        initial_fetch: bool = True,
        recording_enabled: bool = False,
        timeout: Union[int, tuple, None] = None,
        verify_request_ssl: bool = True
    ) -> None:
        """
        :param url: The url to reach your OpenVidu Server instance. Typically something like https://localhost:4443/
        :param secret: Secret for your OpenVidu Server
        :param initial_fetch: Enable the initial fetching on object creation. Defaults to `True`.
                              If set to `False` a `fetch()` must be called before doing anything with the object.
                              In most scenarios you won't need to change this.
        :param timeout: Set timeout to all Requests to the OpenVidu server. Default: None = No timeout.
                        See https://2.python-requests.org/en/latest/user/advanced/#timeouts for possible values.
        :param verify_request_ssl: Defaults to `True`,
                                   requiring requests to verify the TLS certificate at the remote end.
                                   If verify is set to `False`, requests will accept any TLS certificate
                                   presented by the server, and will ignore hostname mismatches and/or
                                   expired certificates, which will make your application vulnerable to
                                   man-in-the-middle (MitM) attacks. Only set this to `False` for testing
        """
        self._session = BaseUrlSession(base_url=url)
        self._session.auth = HTTPBasicAuth('OPENVIDUAPP', secret)
        self._session.verify = verify_request_ssl

        self._session.headers.update({
            'User-Agent': user_agent('PyOpenVidu', __version__)
        })

        self._session.request = partial(self._session.request, timeout=timeout)

        self._openvidu_sessions = {}  # id:object
        self._openvidu_recordings = {}  # id:object

        self._last_fetch_result = {}  # Used only to calculate the return value of the fetch() call
        self._last_fetch_result_recordings = {}

        if initial_fetch:
            self.fetch()  # initial fetch
            if recording_enabled:
                self.fetch_recordings()

    def fetch(self) -> bool:
        """
        Updates every property of every active Session with the current status they have in OpenVidu Server.
        After calling this method you can access the updated list of active sessions trough the `sessions` property.

        :return: true if the Session status has changed with respect to the server, false if not.
                 This applies to any property or sub-property of the object.
        """

        r = self._session.get('sessions')
        r.raise_for_status()
        new_data = r.json()['content']

        data_changed = new_data != self._last_fetch_result
        self._last_fetch_result = new_data

        if data_changed:
            self._openvidu_sessions = {}

            # update, create valid streams
            for session_data in new_data:
                session_id = session_data['id']
                self._openvidu_sessions[session_id] = OpenViduSession(self._session, session_data)

        return data_changed

    def get_session(self, session_id: str) -> OpenViduSession:
        """
        Get a currently active session to the server.

        :param session_id: The ID of the session to acquire.
        :return: An OpenViduSession object.
        """
        if session_id not in self._openvidu_sessions:
            raise OpenViduSessionDoesNotExistsError()

        session = self._openvidu_sessions[session_id]

        if not session.is_valid:
            raise OpenViduSessionDoesNotExistsError()

        return session

    def create_session(
        self,
        media_mode: str = 'ROUTED',
        recording_mode: str = 'MANUAL',
        custom_session_id: Optional[str] = None,
        forced_video_codec: str = 'VP8',
        allow_transcoding: bool = False,
        media_node_id: Optional[str] = None,
        default_recording_name: Optional[str] = None,
        default_recording_has_audio: bool = True,
        default_recording_has_video: bool = True,
        default_recording_output_mode: str = 'COMPOSED',
        default_recording_layout: str = 'BEST_FIT',
        default_recording_resolution: str = '1280x720',
        default_recording_framerate: int = 25,
        default_recording_shm_size: int = 536870912,
        default_recording_media_node_id: Optional[str] = None
    ) -> OpenViduSession:
        """
        Creates a new OpenVidu session.

        This method calls fetch() automatically since the server does not return the proper data
        to construct the OpenViduSession object.

        https://docs.openvidu.io/en/2.20.0/reference-docs/REST-API/#post-session

        :param custom_session_id: You can fix the sessionId that will be assigned to the session with this parameter.
        :param media_mode: ROUTED (default) or RELAYED
        :param recording_mode: MANUAL (default) or ALWAYS
        :param forced_video_codec: VP8 (default) or H264 or None
        :param allow_transcoding: False (default) or True
        :param media_node_id: Media node id (PRO Subscription)
        :param default_recording_name: None (default) or str
        :param default_recording_has_audio: True (default) or False
        :param default_recording_has_video: True (default) or False
        :param default_recording_output_mode: COMPOSED (default) or COMPOSED_QUICK_START or INDIVIDUAL
        :param default_recording_layout: BEST_FIT (default) or CUSTOM
        :param default_recording_resolution: 1280x720 (default) or another
        :param default_recording_framerate: 25 (default) or another
        :param default_recording_shm_size: 536870912 (default) or another
        :param default_recording_media_node_id: Media node id (PRO Subscription)

        :return: The created OpenViduSession instance.
        """

        parameters: dict = {
            'mediaMode': media_mode,
            'recordingMode': recording_mode,
            'customSessionId': custom_session_id,
            'forcedVideoCodec': forced_video_codec,
            'allowTranscoding': allow_transcoding,
            'defaultRecordingProperties': {
                'name': default_recording_name,
                'hasAudio': default_recording_has_audio,
                'hasVideo': default_recording_has_video,
                'outputMode': default_recording_output_mode,
                'recordingLayout': default_recording_layout,
                'resolution': default_recording_resolution,
                'frameRate': default_recording_framerate,
                'shmSize': default_recording_shm_size
            }
        }

        if media_node_id:
            parameters['mediaNode'] = {
                'id': media_node_id
            }

        if default_recording_media_node_id:
            parameters['defaultRecordingProperties']['mediaNode'] = {
                'id': default_recording_media_node_id
            }

        # TODO: Add parameters validation

        # clean keys with None values
        parameters = {k: v for k, v in parameters.items() if v is not None}

        # send request
        r = self._session.post('sessions', json=parameters)

        if r.status_code == 409:
            raise OpenViduSessionExistsError()
        elif r.status_code == 400:
            raise ValueError()

        r.raise_for_status()

        # As of OpenVidu 2.20.0 the server returns the created session object
        new_session = OpenViduSession(self._session, r.json())
        self._openvidu_sessions[new_session.id] = new_session

        return new_session

    @property
    def sessions(self) -> List[OpenViduSession]:
        """
        Get a list of currently active sessions to the server.

        :return: A list of OpenViduSession objects.
        """
        return [
            sess for sess in self._openvidu_sessions.values() if sess.is_valid
        ]

    @property
    def session_count(self) -> int:
        """
        Get the number of active sessions on the server.

        :return: The number of active sessions.
        """
        return len(self.sessions)

    def get_config(self) -> dict:
        """
        Get OpenVidu active configuration.

        Unlike session related calls. This call does not require prior calling of the fetch() method.
        Using this function will always result an API call to the backend.

        https://docs.openvidu.io/en/2.20.0/reference-docs/REST-API/#get-config

        :return: The exact response from the server as a dict.
        """
        # Note: Since 2.16.0 This endpoint is moved from toplevel under /api
        # https://docs.openvidu.io/en/2.16.0/reference-docs/REST-API/#get-openviduapiconfig
        r = self._session.get('config')
        r.raise_for_status()

        return r.json()

    def create_recording(
        self,
        session_id,
        name: Optional[str] = None,
        has_audio: bool = True,
        has_video: bool = True,
        output_mode: str = 'COMPOSED',
        recording_layout: str = 'BEST_FIT',
        custom_layout: Optional[str] = None,
        resolution: str = '1280x720',
        framerate: int = 25,
        shm_size: int = 536870912,
        ignore_failed_streams: bool = True,
        media_node_id: Optional[str] = None
    ) -> OpenViduRecording:
        """
        Start recording

        https://docs.openvidu.io/en/2.20.0/reference-docs/REST-API/#post-recording-start

        """
        session = self.get_session(session_id)

        parameters = {
            'session': session_id,
            'name': name,
            'hasAudio': has_audio,
            'hasVideo': has_video,
            'outputMode': output_mode,
            'recordingLayout': recording_layout,
            'customLayout': custom_layout,
            'resolution': resolution,
            'frameRate': framerate,
            'shmSize': shm_size,
            'ignoreFailedStreams': ignore_failed_streams,
        }

        if media_node_id:
            parameters['mediaNode'] = {
                'id': media_node_id
            }

        # TODO: Add parameters validation

        r = self._session.post(f'recordings/start', json=parameters)

        if r.status_code == 404:
            session.is_valid = False
            raise OpenViduSessionDoesNotExistsError()
        r.raise_for_status()

        new_recording = OpenViduRecording(self._session, r.json())
        self._openvidu_recordings[new_recording.id] = new_recording

        return new_recording

    def fetch_recordings(self) -> dict:
        """
        Get all recordings

        """
        r = self._session.get(f'recordings')
        r.raise_for_status()
        new_data = r.json()['items']

        data_changed = new_data != self._last_fetch_result_recordings
        self._last_fetch_result_recordings = new_data

        if data_changed:
            self._openvidu_recordings = {}

            # update, create valid streams
            for recording_data in new_data:
                recording_id = recording_data['id']
                self._openvidu_recordings[recording_id] = OpenViduRecording(self._session, recording_data)

        return data_changed

    @property
    def recordings(self) -> List[OpenViduRecording]:
        """
        Get a list of currently active recordings to the server.

        :return: A list of OpenViduRecording objects.
        """
        return [
            recording for recording in self._openvidu_recordings.values() if recording.is_valid
        ]

    def get_recording(self, recording_id: str) -> OpenViduRecording:
        """
        Get a currently active recording to the server.

        :param recording_id: The ID of the recording to acquire.
        :return: An OpenViduRecording object.
        """
        if recording_id not in self._openvidu_recordings:
            raise OpenViduRecordingDoesNotExistsError()

        recording = self._openvidu_recordings[recording_id]

        if not recording.is_valid:
            raise OpenViduRecordingDoesNotExistsError()

        return recording

    def get_session_recordings(self, session_id: str) -> List[OpenViduRecording]:
        recordings = []
        for recording in self._openvidu_recordings.values():
            if recording.session_id == session_id:
                if recording.is_valid:
                    recordings.append(recording)
        return recordings
