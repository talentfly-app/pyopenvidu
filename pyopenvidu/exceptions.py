# Base exception


class OpenViduError(BaseException):
    pass


# Session errors

class OpenViduSessionError(OpenViduError):
    pass


class OpenViduSessionDoesNotExistsError(OpenViduSessionError):
    pass


class OpenViduSessionExistsError(OpenViduSessionError):
    pass


# Connection errors

class OpenViduConnectionError(OpenViduSessionError):
    pass


class OpenViduConnectionDoesNotExistsError(OpenViduConnectionError):
    pass


# Stream errors

class OpenViduStreamError(OpenViduConnectionError):
    pass


class OpenViduStreamDoesNotExistsError(OpenViduStreamError):
    pass

# Recording errors

class OpenViduRecordingError(OpenViduSessionError):
    pass


class OpenViduRecordingDoesNotExistsError(OpenViduRecordingError):
    pass

class OpenViduRecordingNotStoppedError(OpenViduRecordingError):
    pass

class OpenViduRecordingNotEnabledError(OpenViduRecordingError):
    pass

class OpenViduRecordingNotStartedError(OpenViduRecordingError):
    pass

