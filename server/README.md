# Server modülü

Bu klasör oyun ve kullanıcı mantığından bağımsız sunucu/yayın katmanıdır.

## Komutlar

```powershell
# Yalnızca web sunucusu
.\.venv\Scripts\python.exe -m server serve

# Web sunucusu ve yapılandırılmış tünel sağlayıcısı
.\.venv\Scripts\python.exe -m server public

# Çalışan sunucu için yalnızca tünel
.\.venv\Scripts\python.exe -m server tunnel
```

## Ortam değişkenleri

- `FOOTBALL_MATCH_HOST`: varsayılan `0.0.0.0`
- `FOOTBALL_MATCH_PORT`: varsayılan `5000`
- `FOOTBALL_MATCH_SECRET_KEY`: verilmezse `instance/server_secret.txt` içinde oluşturulur
- `FOOTBALL_MATCH_TUNNEL_PROVIDER`: varsayılan `cloudflare`
- `FOOTBALL_MATCH_TUNNEL_ORIGIN`: varsayılan `http://127.0.0.1:<port>`
- `CLOUDFLARED_BIN`: isteğe bağlı özel `cloudflared` yolu

Yeni bir tünel veya hosting sağlayıcısı eklemek için `tunnels.py` içindeki `TunnelProvider` sözleşmesini uygulayan adaptör eklenir. Oyun kodu ve `app.py` değiştirilmez.

