# clinic-agent-lab

Versión **0.1.0** · Apache-2.0 · [GitHub: imwyvern](https://github.com/imwyvern)

> **Límites explícitos:** solo datos SYNTHETIC (sintéticos); **not a medical device — no es un dispositivo médico**.
> No realiza diagnósticos, entrenamiento de modelos clínicos ni ejecución automática de órdenes,
> y no es un sistema de producción. Nunca introduzca datos de pacientes reales. Cada propuesta
> conserva el estado MedicationRequest `draft`, incluso después de que un médico de demostración
> confirme la decisión del flujo de trabajo.

[English](../../README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) ·
[日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md)

## Qué hace

Es un pequeño laboratorio de flujos de trabajo en Python. Un agente determinista recopila el
resumen, los análisis, las alergias y los medicamentos de un paciente ficticio, redacta la propuesta
definida en el caso de prueba y genera una tarjeta de seguridad. Un **rol de médico de demostración**
sin autenticación puede confirmar o rechazar una decisión. Muestra métodos de ingeniería para
orquestar herramientas, persistir datos, garantizar idempotencia, aplicar controles de seguridad
y realizar evaluaciones reproducibles. No elige diagnósticos ni tratamientos.

P0 incluye **10 casos de prueba sintéticos** y **4 reglas de elaboración propia** en un **Demo Rule Pack**.
Estas reglas breves y sus límites de dosis arbitrarios son lógica de demostración, no guías clínicas.
Los recursos son JSON simplificados de estilo FHIR, no FHIR completo ni una historia clínica electrónica interoperable.

## Inicio rápido

Requiere Python **3.11+**. Ejecute los comandos desde la raíz de este repositorio.
No necesita claves, modelos externos ni servicios de pago.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m clinic_agent_lab.demo --serve
```

Abra <http://127.0.0.1:8000>. La demostración ejecuta el guion descrito abajo y deja el servidor
local en ejecución. Después del resumen de éxito, Ctrl-C lo detiene con código de salida 0.
La base de datos predeterminada es `.demo/demo.db`; cada ejecución utiliza claves de negocio
ficticias únicas y conserva el historial. Si el puerto 8000 está ocupado, use `--port 8001`
o `--port 0` y consulte la dirección impresa.

Para una demostración desatendida que comprueba las páginas de gestión mediante HTTP real y después termina:

```bash
python -m clinic_agent_lab.demo
```

Imprime la dirección de gestión y un comando para volver a abrir los casos guardados; su servidor
se detiene después de las comprobaciones. También puede iniciar un servidor local independiente
de API y gestión, inicialmente vacío:

```bash
python -m uvicorn clinic_agent_lab.api:app --host 127.0.0.1 --port 8000
```

Ese servidor utiliza `.demo/clinic.db`. Para volver a abrir el historial de la demostración,
establezca `CLINIC_DB_PATH=.demo/demo.db` antes de ejecutar el mismo comando del servidor.
`.env.example` contiene ejemplos de configuración; la aplicación lee variables de entorno
y no carga `.env` automáticamente. El valor predeterminado es `CLINIC_CASE_TTL_SECONDS=300`;
la caducidad se comprueba al acceder, sin un proceso en segundo plano.

## Pasos de la demostración y API

1. Una propuesta normal pasa a `awaiting_physician`; el médico de demostración confirma y la cronología termina en `confirmed`.
2. Una alergia a la clase de las penicilinas genera `block`; confirmar devuelve HTTP 409 y sigue siendo posible rechazar.
3. La ausencia de un análisis obligatorio genera `warn`; se muestran tanto la confirmación como el rechazo.
4. Al repetir un `clientCaseId`, se devuelve el caso original y un único borrador.
5. Un caso con TTL corto pasa a `expired`; una confirmación tardía devuelve HTTP 409.
6. Consulte las páginas de lista y detalle, las tarjetas de seguridad y las cronologías persistidas de herramientas, estados y decisiones.

Con el servidor independiente en ejecución, el [ejemplo mínimo de API](../../examples/api_demo.py) se ejecuta así:

```bash
python examples/api_demo.py
```

API: `GET /api/fixtures`, `POST /api/cases`, `GET /api/cases`,
`GET /api/cases/{id}`, `POST /api/cases/{id}/decision`.
La creación solo acepta `clientCaseId` y un `fixture_id` incluido en el repositorio; no admite cargas de historias clínicas.
Las decisiones aceptan `action` (`confirm`/`reject`), `role`, `actor` y `reason` opcional; solo contenido ficticio.
El rol `physician` es obligatorio para ambas acciones; `observer` recibe HTTP 403.
**No hay autenticación ni verificación de identidad médica.** Vincule el servidor únicamente a la interfaz de bucle local.

## Máquina de estados y semántica de seguridad

```text
accepted → gathering → drafted → awaiting_physician → confirmed | rejected | expired | failed
```

Cualquier estado no terminal puede pasar a `expired` o `failed`. Los estados terminales no se pueden reabrir.
Las herramientas, en orden fijo, son `get_patient_summary`, `get_labs`, `get_allergies`,
`get_medications` y `draft_order`. Las transiciones y las salidas de las herramientas se persisten
en SQLite (`cases`, `events`, `drafts`). La clave de negocio `clientCaseId` es única;
reutilizarla con otro caso de prueba devuelve 409.

Los niveles de tarjeta son `clear`, `caution`, `warn` y `block`; `block` prevalece sobre `warn`.
`caution` está reservado y ninguna regla P0 lo emite. Una tarjeta `clear` indica que no se activaron
reglas de demostración; no constituye evidencia de seguridad clínica. Cada tarjeta contiene los ID
de las reglas, los datos ausentes, los conflictos, una explicación y el borrador. La confirmación
de una propuesta bloqueada se rechaza sin cambiar `awaiting_physician`; todavía puede rechazarse
o caducar. Los otros niveles permiten una decisión del médico de demostración.
**Ningún nivel ejecuta una orden.**

## Evaluación

```bash
ruff check .
pytest
python -m clinic_agent_lab.evaluate --output .demo/evaluation.json
python scripts/check_docs.py
```

Las pruebas fijan los bloqueos etiquetados por alergia o dosis, el rechazo de confirmaciones bloqueadas,
el comportamiento de advertencia sin bloqueo y sus dos decisiones, la idempotencia ante repeticiones
y concurrencia, la caducidad, la ausencia de ejecución, el determinismo y la coherencia documental.
La evaluación solo informa de activaciones de reglas y comprobaciones del flujo realizadas sobre
los casos de prueba. No afirma exactitud diagnóstica, concordancia con médicos ni latencia.
Consulte los [resultados y el método](../evaluation.md), con la fecha real de ejecución en HKT.

## Contenedor local

```bash
docker build -t clinic-agent-lab:local .
docker run --rm -p 127.0.0.1:8000:8000 clinic-agent-lab:local
```

Esto ejecuta la API y las páginas locales, no el guion de demostración. Los datos del contenedor
son efímeros salvo que monte un directorio local en `/app/data`. Es una imagen de conveniencia,
no un despliegue de producción.

## Shipped — Entregado

P0: Python/FastAPI/Pydantic v2, máquina de estados SQLite, herramientas deterministas, 10 casos
de prueba sintéticos, 4 reglas de demostración, tarjetas de seguridad, controles del rol médico,
gestión HTML, demostración mediante HTTP real, evaluación de casos, pruebas, lint, archivo de
flujo de CI, Dockerfile local y documentación en seis idiomas. Esta implementación se validó localmente;
un archivo de flujo de CI por sí solo no acredita el estado de la CI alojada ni la existencia de una versión publicada.

## Planned — Planificado

P1/T8 queda fuera de esta versión: reescritura opcional del texto mediante LLM que no pueda cambiar
las decisiones de las reglas, importación de Synthea con licencia verificada y un pequeño clasificador
de referencia basado en características sintéticas. Ninguno está implementado. No hay entrenamiento
de modelos clínicos, integración hospitalaria ni adaptador de ejecución.

## Límites de experiencia y descargo de responsabilidad

El autor utiliza principalmente TypeScript/Node para desarrollo de backend. Su experiencia con Python
incluye Django, FastAPI, py-agents y proyectos personales; Python no es su tecnología principal diaria.
No tiene experiencia de entrenamiento con datos clínicos, de integración con sistemas hospitalarios,
una titulación que habilite para ejercer medicina ni experiencia de desarrollo conjunto de sistemas
clínicos con médicos. Este laboratorio muestra agentes de flujos de trabajo, controles de seguridad
y evaluación reproducible; no acredita experiencia clínica ni preparación para uso clínico.

Utilice únicamente los casos ficticios incluidos. No use las salidas para atención real, prescripción,
diagnóstico ni decisiones operativas. La confirmación solo registra una decisión local de demostración.

## Documentación, contribución y licencia

[Arquitectura](../architecture.md) · [Reglas y tarjetas](../rules-and-safety.md) ·
[Datos y licencia](../data-and-license.md) · [Seguridad](../../SECURITY.md) ·
[Contribución](../../CONTRIBUTING.md) · [Historial de cambios](../../CHANGELOG.md)

Código, casos de prueba originales y documentación: [Apache-2.0](../../LICENSE), con [NOTICE](../../NOTICE).
Contacto: wpkreg@gmail.com · GitHub: [imwyvern](https://github.com/imwyvern).
