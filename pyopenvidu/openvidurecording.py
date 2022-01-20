"""OpenViduRecording class."""
from dataclasses import dataclass
from requests_toolbelt.sessions import BaseUrlSession
from .exceptions import OpenViduRecordingDoesNotExistsError, OpenViduSessionDoesNotExistsError, \
    OpenViduRecordingNotStoppedError, OpenViduRecordingNotEnabledError, \
    OpenViduRecordingNotStartedError
from datetime import datetime


@dataclass(init=False, frozen=False)
class OpenViduRecording(object):
    """
    This is a base class for recording objects.

    https://docs.openvidu.io/en/2.20.0/reference-docs/REST-API/#the-recording-object

    """

    id: str
    name: str
    output_mode: str
    has_audio: bool
    has_video: bool
    resolution: str
    frame_rate: int
    recording_layout: str
    custom_layout: str
    session_id: str
    created_at: datetime
    size: int
    duration: float
    url: str
    status: str  # starting, started, stopped, ready, failed
    is_valid: bool

    def _update_from_data(self, data: dict):
        # set property
        self.id = data['id']
        self.name = data['name']
        self.output_mode = data['outputMode']
        self.has_audio = data['hasAudio']
        self.has_video = data['hasVideo']
        self.resolution = data.get('resolution', None)
        self.frame_rate = data.get('frameRate', None)
        self.recording_layout = data.get('recordingLayout', None)
        self.custom_layout = data.get('customLayout', None)
        self.session_id = data['sessionId']
        self.created_at = datetime.utcfromtimestamp(data['createdAt'] / 1000.0)
        self.size = data['size']
        self.duration = data['duration']
        self.url = data['url']
        self.status = data['status']
        # self.server_data = data.get('serverData', None)
        self.is_valid = True

    def __init__(
        self,
        session: BaseUrlSession,
        data: dict,
        verify_request_ssl: bool = True
    ) -> None:
        """
        This is meant for internal use, thus you should not call it.
        Use `OpenViduSession.connections` to get an instance of this class.
        """

        self._session = session
        self._session.verify = verify_request_ssl
        self._update_from_data(data)
        self._last_fetch_result = data

    def fetch(self) -> bool:
        """
        Updates every property of the connection object.

        :return: true if the Connection object status has changed with respect to the server,
        false if not. This applies to any property or sub-property of the object.
        """

        if not self.is_valid:
            raise OpenViduRecordingDoesNotExistsError()

        r = self._session.get(f'recordings/{self.id}')
        if r.status_code == 404:
            self.is_valid = False
            raise OpenViduRecordingDoesNotExistsError()
        elif r.status_code == 400:
            self.is_valid = False
            raise OpenViduSessionDoesNotExistsError()

        r.raise_for_status()
        new_data = r.json()

        is_changed = new_data != self._last_fetch_result

        if is_changed:
            self._update_from_data(new_data)
            self._last_fetch_result = new_data

        return is_changed

    def delete(self) -> bool:
        if not self.is_valid:
            raise OpenViduRecordingDoesNotExistsError()

        r = self._session.delete(f'recordings/{self.id}')
        if r.status_code == 404:
            self.is_valid = False
            raise OpenViduRecordingDoesNotExistsError()
        elif r.status_code == 409:
            raise OpenViduRecordingNotStoppedError()
        elif r.status_code == 501:
            self.is_valid = False
            raise OpenViduRecordingNotEnabledError()

        r.raise_for_status()
        self.is_valid = False
        return True

    def stop(self) -> bool:
        if not self.is_valid:
            raise OpenViduRecordingDoesNotExistsError()

        r = self._session.post(f'recordings/stop/{self.id}', json={})
        if r.status_code == 404:
            self.is_valid = False
            raise OpenViduRecordingDoesNotExistsError()
        elif r.status_code == 406:
            raise OpenViduRecordingNotStartedError()
        elif r.status_code == 501:
            self.is_valid = False
            raise OpenViduRecordingNotEnabledError()

        r.raise_for_status()
        return True
