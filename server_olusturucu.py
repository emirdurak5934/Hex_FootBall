"""FootballDatabase sunucusunu kolayca başlatan kullanıcı arayüzü.

Bu dosya oyun veya tünel mantığı içermez. Proje konumunu kendi dosyasından
hesaplar ve bağımsız ``server`` modülünü uygun komutla çalıştırır.
"""

import argparse
import json
import os
import socket
import subprocess
import sys


PROJE_KLASORU = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(PROJE_KLASORU, ".venv", "Scripts", "python.exe")
VARSAYILAN_PORT = 5000
TUNEL_DURUM_DOSYASI = os.path.join(PROJE_KLASORU, "instance", "active_tunnel.json")


def python_yolunu_bul() -> str:
    """Önce projedeki sanal ortamı, yoksa çalışan Python'u kullan."""
    if os.path.isfile(VENV_PYTHON):
        return VENV_PYTHON
    return sys.executable


def port_acik_mi(port: int = VARSAYILAN_PORT) -> bool:
    """Yerel sunucunun belirtilen portta cevap verip vermediğini kontrol et."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as baglanti:
        baglanti.settimeout(0.4)
        return baglanti.connect_ex(("127.0.0.1", port)) == 0


def yerel_ip_bul() -> str:
    """Telefonda kullanılabilecek yerel ağ adresini mümkünse tespit et."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as baglanti:
        try:
            baglanti.connect(("8.8.8.8", 80))
            return baglanti.getsockname()[0]
        except OSError:
            return "BILINEMEDI"


def surec_calismakta_mi(process_id: int) -> bool:
    try:
        os.kill(process_id, 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def aktif_public_url() -> str | None:
    try:
        with open(TUNEL_DURUM_DOSYASI, "r", encoding="utf-8") as source:
            durum = json.load(source)
        url = durum.get("url")
        process_id = durum.get("pid")
        if isinstance(url, str) and isinstance(process_id, int) and surec_calismakta_mi(process_id):
            return url
    except (OSError, ValueError, AttributeError):
        pass
    return None


def aktif_adresleri_goster() -> None:
    print("\n" + "=" * 72)
    if port_acik_mi():
        print("AKTİF YEREL SUNUCU ADRESİ:")
        print(f"http://{yerel_ip_bul()}:{VARSAYILAN_PORT}")
    else:
        print("YEREL SUNUCU: KAPALI")

    public_url = aktif_public_url()
    if public_url:
        print("\nAKTİF PUBLIC SUNUCU ADRESİ:")
        print(public_url)
    else:
        print("\nPUBLIC SUNUCU: KAPALI VEYA ADRES HENÜZ HAZIR DEĞİL")
    print("=" * 72 + "\n")


def sistem_kontrolu() -> bool:
    python_yolu = python_yolunu_bul()
    print(f"Proje : {PROJE_KLASORU}")
    print(f"Python: {python_yolu}")
    print(f"Port {VARSAYILAN_PORT}: {'KULLANILIYOR' if port_acik_mi() else 'BOS'}")
    aktif_adresleri_goster()

    kontrol = subprocess.run(
        [python_yolu, "-c", "import flask, flask_socketio"],
        cwd=PROJE_KLASORU,
        capture_output=True,
        text=True,
        check=False,
    )
    if kontrol.returncode != 0:
        print("\nEksik Python paketleri var.")
        print(r"Kurulum: .\.venv\Scripts\python.exe -m pip install -r requirements.txt")
        return False

    print("Gerekli Python paketleri hazır.")
    return True


def sunucuyu_baslat(komut: str) -> int:
    if komut in {"serve", "public"} and port_acik_mi():
        aktif_adresleri_goster()
        print(f"\nPort {VARSAYILAN_PORT} zaten kullanımda.")
        print("Sunucu zaten açıksa yeni bir kopya başlatmayın; açık pencereyi kullanın.")
        return 1

    if not sistem_kontrolu():
        return 1

    if komut == "serve":
        print(f"\nTelefon adresi: http://{yerel_ip_bul()}:{VARSAYILAN_PORT}")
        print("Telefon ve bilgisayar aynı Wi-Fi ağında olmalı.")
    elif komut == "public":
        print("\nCloudflare bağlantısı hazırlanıyor.")
        print("PUBLIC_URL= satırındaki bağlantıyı iki telefonda da açın.")
    else:
        print("\nYalnızca Cloudflare tüneli başlatılıyor.")

    print("Durdurmak için Ctrl+C tuşlarına basın.\n")
    try:
        sonuc = subprocess.run(
            [python_yolunu_bul(), "-m", "server", komut],
            cwd=PROJE_KLASORU,
            check=False,
        )
        return sonuc.returncode
    except KeyboardInterrupt:
        print("\nSunucu kapatıldı.")
        return 0


def menu() -> str | None:
    aktif_adresleri_goster()
    print("\n=== FootballDatabase Sunucu Oluşturucu ===")
    print("1 - Aynı Wi-Fi ağında çalıştır")
    print("2 - İnternete aç (Sunucu + Cloudflare)")
    print("3 - Yalnızca Cloudflare tüneli")
    print("4 - Sistem ve port kontrolü")
    print("0 - Çıkış")
    secim = input("\nSeçiminiz: ").strip()
    return {
        "1": "serve",
        "2": "public",
        "3": "tunnel",
        "4": "check",
        "0": None,
    }.get(secim, "gecersiz")


def pencereyi_acik_tut() -> None:
    """Çift tıklamayla açılan pencerenin hata mesajını göstermeden kapanmasını önle."""
    try:
        input("\nBu pencereyi kapatmak için Enter'a basın...")
    except (EOFError, KeyboardInterrupt):
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="FootballDatabase sunucu oluşturucu")
    parser.add_argument(
        "komut",
        nargs="?",
        choices=("serve", "public", "tunnel", "check"),
        help="Menüyü kullanmadan çalıştırılacak işlem",
    )
    args = parser.parse_args()
    menu_kullanildi = args.komut is None
    komut = args.komut

    try:
        if komut is None:
            komut = menu()
            if komut == "gecersiz":
                print("Geçersiz seçim.")
                return 2
            if komut is None:
                return 0

        if komut == "check":
            return 0 if sistem_kontrolu() else 1
        return sunucuyu_baslat(komut)
    except Exception as hata:
        print(f"\nSUNUCU BAŞLATILAMADI: {hata}")
        return 1
    finally:
        if menu_kullanildi:
            pencereyi_acik_tut()


if __name__ == "__main__":
    raise SystemExit(main())
