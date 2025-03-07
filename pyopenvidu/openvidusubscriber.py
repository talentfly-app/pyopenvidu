"""OpenViduSubscriber class."""
from requests_toolbelt.sessions import BaseUrlSession
from dataclasses import dataclass
from datetime import datetime


# Notice: Frozen should be changed to True in later versions of Python3
# where a nice method for custom initializer is implemented
@dataclass(frozen=False, init=False)
class OpenViduSubscriber(object):
    session_id: str
    stream_id: str
    created_at: datetime

    def __init__(
        self,
        session: BaseUrlSession,
        session_id: str,
        data: dict,
        verify_request_ssl: bool = True
    ) -> None:
        """
        This is meant for internal use, thus you should not call it.
        Use `OpenViduConnection.subscribers` to get an instance of this class.
        """

        self._session = session
        self._session.verify = verify_request_ssl
        self.session_id = session_id
        self.stream_id = data['streamId']
        self.created_at = datetime.utcfromtimestamp(data['createdAt'] / 1000.0)
