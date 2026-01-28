from django.shortcuts import render, get_object_or_404
from .models import ProtectionProtocol

def protection_protocol_view(request):
    protocol = get_object_or_404(
        ProtectionProtocol,
        is_active=True
    )
    return render(
        request,
        "legal/protection_protocol.html",
        {"protocol": protocol}
    )
