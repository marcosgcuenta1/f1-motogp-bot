# 🏁 Bot de Telegram — F1 y MotoGP

Bot que se ejecuta en **GitHub Actions** (gratis, sin servidor propio) y:

1. **Los jueves por la tarde**, si el fin de semana hay **F1** o **MotoGP**, te
   envía un mensaje con **todos los horarios** (libres, clasificación, sprint y
   carrera) en **hora de Madrid**.
2. **~10 minutos antes de cada carrera** (solo carreras, no clasificaciones) te
   avisa: *"¡Quedan 10 minutos para que empiece!"*.

## Fuentes de datos (gratuitas)

- **F1** → [jolpica-f1](https://github.com/jolpica/jolpica-f1) (`api.jolpi.ca`),
  sucesor de Ergast.
- **MotoGP** → API pública no oficial de motogp.com
  (`api.motogp.pulselive.com`). Se filtra la clase reina (MotoGP, no Moto2/Moto3).

> Si MotoGP no devuelve datos, la F1 sigue funcionando (los fallos de una
> fuente no tumban el bot).

## Puesta en marcha

### 1. Consigue tu `chat id`
Abre Telegram, envía un mensaje cualquiera a tu bot y luego:

```bash
pip install -r requirements.txt
python get_chat_id.py <TU_TOKEN>
```

Apunta el `chat id` que imprime.

### 2. Sube esto a un repositorio de GitHub
```bash
git init
git add .
git commit -m "Bot F1/MotoGP"
git branch -M main
git remote add origin <tu-repo>
git push -u origin main
```

### 3. Configura los secretos
En el repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret               | Valor                          |
|----------------------|--------------------------------|
| `TELEGRAM_BOT_TOKEN` | el token de tu bot             |
| `TELEGRAM_CHAT_ID`   | el chat id del paso 1          |

### 4. Activa los workflows
En la pestaña **Actions** habilita los workflows. Puedes lanzarlos a mano con
**"Run workflow"** (`workflow_dispatch`) para probarlos sin esperar al cron.

## Prueba en local (opcional)

```bash
# PowerShell
$env:TELEGRAM_BOT_TOKEN = "..."
$env:TELEGRAM_CHAT_ID   = "..."
python run_weekend_summary.py
python run_race_alert.py
```

## Notas importantes

- **Horario de verano:** GitHub Actions usa siempre UTC. El resumen está fijado
  a las **17:00 UTC del jueves** (= 19:00 en Madrid en verano, 18:00 en
  invierno). Si quieres clavar la hora todo el año, ajusta el `cron` en
  [resumen-finde.yml](.github/workflows/resumen-finde.yml) al cambiar la hora.
- **Precisión del aviso de 10 min:** el cron de GitHub se ejecuta cada 5 minutos
  pero puede retrasarse en momentos de mucha carga. Por eso el aviso usa una
  ventana de 12 minutos: en la práctica el mensaje llega entre ~7 y ~12 minutos
  antes de la carrera. Para precisión exacta haría falta un servidor siempre
  encendido.
- **Minutos de Actions:** en un repo **público** los minutos son ilimitados.
  En uno **privado** tienes 2.000 min/mes gratis; el cron cada 5 min en finde
  consume parte de esa cuota (puedes reducir la franja horaria del cron).
- **Sprints:** por defecto solo avisa de la carrera principal. Para avisar
  también de la carrera al sprint, añade el secreto/variable `ALERT_SPRINTS=1`.

## Estructura

```
bot/
  sources.py          # descarga y normaliza horarios de F1 + MotoGP
  messages.py         # construye los textos del resumen y del aviso
  telegram_client.py  # envío a la Bot API de Telegram
  state.py            # deduplicación de avisos ya enviados
run_weekend_summary.py # job de los jueves
run_race_alert.py      # job de aviso 10 min antes
get_chat_id.py         # utilidad para obtener tu chat id
.github/workflows/     # crons de GitHub Actions
data/alerted.json      # estado de avisos enviados (lo gestiona el bot)
```
