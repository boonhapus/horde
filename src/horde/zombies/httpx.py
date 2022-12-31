from __future__ import annotations
import datetime as dt

import httpx

from horde import Zombie
import horde.events


class HTTPXZombie(Zombie):
    """
    """

    def __init__(self, environment, zombie_id: int):
        super().__init__(environment, zombie_id)
        self.client = httpx.AsyncClient(base_url=self.environment.host, event_hooks={"response": [self.on_response]})

    def _build_error_from_response(self, response: httpx.Response) -> httpx.HTTPStatusError:
        if response.is_success:
            return None

        # Taken from httpx.Response.raise_for_status
        # https://github.com/encode/httpx/blob/e5bc1ea533aa5cfcc4f7b179e9faa27f689ed91f/httpx/_models.py#L714
        template = (
            "{error_type} '{0.status_code} {0.reason_phrase}' for url '{0.url}'\n"
            "For more information check: https://httpstatuses.com/{0.status_code}"
        )

        status_class = response.status_code // 100
        error_types = {1: "Informational response", 3: "Redirect response", 4: "Client error", 5: "Server error"}
        error_type = error_types.get(status_class, "Invalid status code")
        message = template.format(response, error_type=error_type)
        return httpx.HTTPStatusError(message, request=response.request, response=response)

    async def on_response(self, r: httpx.Response) -> None:
        """
        Hook into all requests to capture and send metadata to Swarm.
        """
        # needed to determin .elapsed and .content
        await r.aread()

        metadata = {
            "request": r.request,
            "response": r,
            "request_url": r.request.url,
            "request_start_time": dt.datetime.now() - r.elapsed,
            "response_elapsed_time": r.elapsed,
            "response_length": len(r.content or b""),
            "exception": self._build_error_from_response(r),
        }

        self.environment.events.fire(horde.events.EVT_REQUEST_COMPLETE, **metadata)
