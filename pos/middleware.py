from django.shortcuts import redirect
from django.urls import reverse
from .models import CashDrawerSession


class CashDrawerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Verificar solo si el usuario está autenticado y accediendo al POS
        if (request.user.is_authenticated and
                not (request.user.is_staff or request.user.is_superuser)):

            # URLs que NO requieren sesión activa
            excluded_paths = [
                '/pos/open-session/',
                '/pos/close-session/',
                '/logout/',
                '/accounts/',
                '/admin/'
            ]

            # Si está intentando acceder al POS sin sesión activa
            if (request.path.startswith('/pos/') and
                    not any(request.path.startswith(path) for path in excluded_paths)):

                # Verificar si tiene una sesión de caja activa
                has_active_session = CashDrawerSession.objects.filter(
                    user=request.user,
                    end_time__isnull=True
                ).exists()

                if not has_active_session:
                    # Redirigir a apertura de caja si no tiene sesión activa
                    return redirect('open_session')

        response = self.get_response(request)
        return response