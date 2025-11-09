from rest_framework.throttling import ScopedRateThrottle

class RadarScopedRateThrottle(ScopedRateThrottle):
    scope_attr = "throttle_scope"
