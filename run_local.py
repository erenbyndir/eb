"""Interactive local launcher. OAuth credentials remain in process memory."""
import getpass
import os
import runpy
from pathlib import Path

if __name__ == '__main__':
    print('Creator Studio — yerel başlatma')
    print('Google > Clients > istemcin > Authorized redirect URIs alanına şunu ekle:')
    print('http://localhost:3000/auth/callback')
    print('Bu adres, paneli bu bilgisayarda açtığında geçerlidir.\n')
    os.environ['HOST'] = '127.0.0.1'
    os.environ['PORT'] = '3000'
    os.environ['YOUTUBE_REDIRECT_URI'] = 'http://localhost:3000/auth/callback'
    if not os.environ.get('YOUTUBE_CLIENT_ID'):
        os.environ['YOUTUBE_CLIENT_ID'] = input('Client ID: ').strip()
    if not os.environ.get('YOUTUBE_CLIENT_SECRET'):
        os.environ['YOUTUBE_CLIENT_SECRET'] = getpass.getpass('Client secret (yazarken görünmez): ').strip()
    if not os.environ['YOUTUBE_CLIENT_ID'] or not os.environ['YOUTUBE_CLIENT_SECRET']:
        raise SystemExit('İstemci bilgileri boş olamaz.')
    print('\nTarayıcında http://localhost:3000 adresini aç. Ardından YouTube’u bağla düğmesine bas.')
    print('Bu pencere açık kalmalı. Durdurmak için Ctrl+C. Bilgiler dosyaya kaydedilmez.\n')
    try:
        runpy.run_path(str(Path(__file__).resolve().parent / 'server.py'), run_name='__main__')
    except KeyboardInterrupt:
        print('\nSunucu kapatıldı.')
