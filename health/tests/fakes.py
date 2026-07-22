"""Hand-rolled HTTP fakes (no mocking library in the workspace)."""


class FakeResponse:
    def __init__(
        self, status_code=200, json_data=None, headers=None, text=None, malformed_json=False
    ):
        self.status_code = status_code
        self._json = json_data
        self.headers = headers or {}
        # `text` backs the ApiError fallback message when a non-2xx body has no
        # parseable Google error envelope; default to a JSON dump so callers
        # that only pass json_data still get a readable fallback.
        if text is not None:
            self.text = text
        elif json_data is not None:
            self.text = str(json_data)
        else:
            self.text = ""
        self._malformed = malformed_json

    def json(self):
        if self._malformed:
            raise ValueError("Expecting value: malformed JSON body")
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, queue=None):
        self.queue = list(queue or [])
        self.calls = []

    def _record(self, method, url, **kw):
        self.calls.append({"method": method, "url": url, **kw})
        item = self.queue.pop(0)
        if isinstance(item, Exception):
            raise item  # simulate a network error (e.g. requests.ConnectionError)
        return item

    def get(self, url, headers=None, params=None, timeout=None):
        return self._record("GET", url, headers=headers, params=params)

    def post(self, url, json=None, data=None, auth=None, headers=None, timeout=None):
        return self._record("POST", url, json=json, data=data, auth=auth, headers=headers)


class FakeClock:
    """Deterministic monotonic-style clock paired with a wait recorder.

    `wait()` advances the clock instead of sleeping, so pacing tests run
    instantly and still observe realistic elapsed time between sends. Pass
    `.now` as `clock=` and `.sleep` as `wait=` to HealthClient.
    """

    def __init__(self, start: float = 0.0):
        self.value = start
        self.waits: list[float] = []

    def now(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.waits.append(seconds)
        self.value += seconds

    def advance(self, seconds: float) -> None:
        """Move time forward without recording a wait (e.g. to simulate work
        that happened between two sends without the client itself pacing)."""
        self.value += seconds
