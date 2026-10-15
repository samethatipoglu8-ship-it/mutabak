"""Mutabakat Pro giriş noktası.

Çalıştırmak için:  python main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

_file_log_sink_id: int | None = None


def configure_windows_app_id() -> bool:
    """Windows'a paketlenmiş uygulama için sabit bir UI kimliği bildir."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        result = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "MutabakatPro.Desktop")
        return result == 0
    except (AttributeError, OSError):
        return False


def configure_logging() -> int | None:
    """Dosya logunu uygulama gerçekten başlarken bir kez etkinleştir.

    Modülün yalnızca import edilmesi (test keşfi, araçlar, statik analiz)
    kullanıcının gerçek profilinde klasör/log oluşturmamalıdır.
    """
    global _file_log_sink_id
    if _file_log_sink_id is not None:
        return _file_log_sink_id
    try:
        log_dir = Path.home() / ".mutabakat_pro" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        _file_log_sink_id = logger.add(
            log_dir / "mutabakat_{time:YYYY-MM-DD}.log", rotation="1 day",
            retention="30 days", encoding="utf-8", level="INFO")
    except OSError as exc:
        # Loglama yardımcı özelliktir; profil salt-okunursa ana uygulama açılır.
        logger.warning("Dosya logu etkinleştirilemedi: {}", exc)
        return None
    return _file_log_sink_id


def configure_ai() -> None:
    """Direct Line ayarını tek güvenli kaynaktan yükle.

    Secret asla kaynak kodda tutulmaz. ``ai_config`` yalnızca ortam
    değişkenlerini ve yerel geliştirme için git dışındaki ``.env`` dosyasını
    çözer. Secret yoksa AI fallback kapalı kalır; finansal mutabakat ve
    insan inceleme akışı çalışmaya devam eder.
    """
    try:
        from app.incoming.ai_config import configure, status_line

        configure()
        logger.info(status_line())
    except Exception as exc:  # noqa: BLE001 - AI ayarı ana akışı düşürmez
        logger.warning(f"Direct Line yapılandırması uygulanamadı: {exc}")


def configure_backup() -> None:
    """Açılışta otomatik ŞİFRELİ yedek al (günde bir).

    Parola ``MUTABAKAT_BACKUP_PASSWORD`` ortam değişkeninden ya da ayar
    dosyasından gelir. PAROLA YOKSA YEDEK ALINMAZ: şifresiz bir yedek
    yazmak, "yedeğim şifreli" sanan kullanıcıyı yanıltır.
    """
    try:
        from app.services.backup import auto_backup, resolve_password
        from app.services.settings import Settings

        parola = resolve_password(Settings())
        if not parola:
            logger.info(
                "Otomatik yedek KAPALI: yedek parolası tanımlı değil "
                "(MUTABAKAT_BACKUP_PASSWORD).")
            return
        sonuc = auto_backup(parola)
        if sonuc is None:
            logger.info("Otomatik yedek: bugünün yedeği zaten alınmış.")
        elif sonuc.ok:
            logger.info(f"Otomatik yedek alındı ({sonuc.scheme}): {sonuc.path}")
        else:
            logger.warning(f"Otomatik yedek alınamadı: {sonuc.error}")
    except Exception as exc:  # noqa: BLE001 - yedek uygulamayı açmayı engellemez
        logger.warning(f"Otomatik yedek çalıştırılamadı: {exc}")


def run() -> int:
    configure_windows_app_id()
    configure_logging()
    configure_ai()
    configure_backup()
    from app.ui.main_window import main
    return main()


if __name__ == "__main__":
    sys.exit(run())
