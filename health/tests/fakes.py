"""Hand-rolled HTTP fakes (no mocking library in the workspace)."""


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, headers=None):
        self.status_code = status_code
        self._json = json_data
        self.headers = headers or {}

    def json(self):
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

    def get(self, url, headers=None, timeout=None):
        return self._record("GET", url, headers=headers)

    def post(self, url, data=None, auth=None, headers=None, timeout=None):
        return self._record("POST", url, data=data, auth=auth, headers=headers)
