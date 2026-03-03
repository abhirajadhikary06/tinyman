from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock


def _utc_now() -> datetime:
	return datetime.now(timezone.utc)


@dataclass
class UsageEvent:
	provider: str
	created_at: datetime


class UsageTracker:
	def __init__(self):
		self._events: list[UsageEvent] = []
		self._lock = Lock()

	def record(self, provider: str):
		with self._lock:
			self._events.append(UsageEvent(provider=provider, created_at=_utc_now()))
			self._trim_locked()

	def _trim_locked(self):
		cutoff = _utc_now() - timedelta(days=7)
		self._events = [evt for evt in self._events if evt.created_at >= cutoff]

	def snapshot(self) -> list[UsageEvent]:
		with self._lock:
			self._trim_locked()
			return list(self._events)


tracker = UsageTracker()


def record_tinyfish_usage():
	tracker.record("tinyfish")


def record_fireworks_usage():
	tracker.record("fireworks")


def _build_hourly_series(events: list[UsageEvent], provider: str, hours: int = 12) -> dict:
	now = _utc_now().replace(minute=0, second=0, microsecond=0)
	start = now - timedelta(hours=hours - 1)
	buckets = defaultdict(int)

	for event in events:
		if event.provider != provider:
			continue
		hour_key = event.created_at.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
		if start <= hour_key <= now:
			buckets[hour_key] += 1

	labels: list[str] = []
	values: list[int] = []
	for i in range(hours):
		hour = start + timedelta(hours=i)
		labels.append(hour.strftime("%H:%M"))
		values.append(buckets.get(hour, 0))

	return {
		"labels": labels,
		"values": values,
		"total_last_12h": sum(values),
		"peak": max(values) if values else 0,
	}


def get_usage_payload() -> dict:
	events = tracker.snapshot()
	now = _utc_now()
	today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

	tinyfish_today = sum(1 for event in events if event.provider == "tinyfish" and event.created_at >= today_start)
	fireworks_today = sum(1 for event in events if event.provider == "fireworks" and event.created_at >= today_start)

	return {
		"generated_at": now.isoformat(),
		"tinyfish": {
			"name": "TinyFish",
			"color": "#FF6700",
			"series": _build_hourly_series(events, "tinyfish", hours=12),
			"today_calls": tinyfish_today,
		},
		"fireworks": {
			"name": "Fireworks",
			"color": "#6720FF",
			"series": _build_hourly_series(events, "fireworks", hours=12),
			"today_calls": fireworks_today,
		},
	}
