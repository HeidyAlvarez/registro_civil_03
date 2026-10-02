# Cifrado de datos personales

Los datos personales de Citas y del módulo de IA se guardan con AES-256-GCM. Cada valor lleva un nonce aleatorio y una etiqueta de autenticación. El formato es `enc:{version}:{payload}`. La CURP también tiene un índice ciego HMAC-SHA256 en `curp_hash`, porque el texto cifrado no permite búsquedas por igualdad.

Las claves no viven en el repositorio. En producción la aplicación no arranca si faltan.

## Variables

- `PII_ENCRYPTION_KEYS`: objeto JSON, por ejemplo `{"v1":"<clave>","v2":"<clave>"}`. Cada clave es Base64 URL-safe de 32 bytes.
- `PII_ACTIVE_KEY_VERSION`: versión que se usa para cifrar datos nuevos, por ejemplo `v1`.
- `PII_BLIND_INDEX_KEY`: clave distinta, también Base64 URL-safe de 32 bytes. Si cambia, las búsquedas por CURP dejan de encontrar registros anteriores.

También se aceptan los nombres anteriores `DATA_ENCRYPTION_KEYS`, `DATA_ENCRYPTION_ACTIVE_KEY` y `DATA_BLIND_INDEX_KEY`.

## Generar claves

```bash
python manage.py generar_claves_pii
```

El comando solo imprime las claves. Guárdalas en el administrador de secretos de Render o en el entorno local. No las pegues en el código, en fixtures ni en capturas.

## Orden de despliegue

1. Genera las claves y configúralas en Render como variables con `sync: false`. `render.yaml` ya declara `PII_ENCRYPTION_KEYS`, `PII_ACTIVE_KEY_VERSION` y `PII_BLIND_INDEX_KEY`.
2. Haz un respaldo de PostgreSQL con `pg_dump` antes de migrar. Conserva ese archivo fuera del repositorio.
3. Restaura el respaldo en una copia y ejecuta ahí `python manage.py migrate`.
4. En la copia, ejecuta `python manage.py verificar_cifrado_pii`. El comando imprime conteos, nunca valores. Debe terminar sin filas en texto claro.
5. Revisa que agendar, consultar por folio y CURP, cancelar, el comprobante PDF y las notificaciones sigan funcionando.
6. Solo después migra la base que recibe tráfico y vuelve a verificar.
7. Revoca cualquier clave de API que haya quedado expuesta y no la vuelvas a escribir en el repositorio.

Si faltan las claves, la migración se detiene antes de modificar registros.

## Rotación

1. Agrega `v2` dentro de `PII_ENCRYPTION_KEYS` sin borrar `v1`.
2. Cambia `PII_ACTIVE_KEY_VERSION` a `v2`.
3. Ejecuta `python manage.py rotar_claves_pii`.
4. Verifica los conteos. Conserva `v1` hasta confirmar que ya no quedan valores `enc:v1:`.
5. No rotes `PII_BLIND_INDEX_KEY` salvo que vuelvas a calcular todos los `curp_hash`.

## Reversión

Mientras `v1` siga configurada, las migraciones `citas.0007_cifrar_datos_personales` e `ia.0002_cifrar_datos_personales` pueden revertirse. Haz otro respaldo antes de revertir. La reversión descifra y vuelve a dejar las columnas en su tipo anterior.

## Desarrollo local

Con `DEBUG=True` el proceso arranca sin claves, pero guardar o leer datos personales falla hasta que existan. Expórtalas en la terminal antes de `migrate` y `runserver`. Las pruebas de Django usan claves fijas de prueba; no sirven para datos reales.
