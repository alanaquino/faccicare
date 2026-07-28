def unread_notifications(request):
    if request.user.is_authenticated:
        from .models import Notificacion
        Notificacion.seed_for_user(request.user)
        base = Notificacion.objects.filter(usuario=request.user, archivada=False, leida=False)
        total_count = base.count()
        msg_count = base.filter(tipo=Notificacion.TipoNotificacion.MENSAJE).count()
        general_count = base.exclude(tipo=Notificacion.TipoNotificacion.MENSAJE).count()
        return {
            'unread_notifications_count': general_count,
            'unread_messages_count': msg_count,
            'unread_total_count': total_count,
        }
    return {
        'unread_notifications_count': 0,
        'unread_messages_count': 0,
        'unread_total_count': 0,
    }
