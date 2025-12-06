# Cómo Subir el Proyecto a GitHub

## Paso 1: Verificar que .env no se suba

El archivo `.env` contiene tus credenciales y **NO debe subirse a GitHub**. Verifica que esté en `.gitignore`:

```bash
git check-ignore .env
```

Si el comando devuelve `.env`, está correctamente ignorado. ✅

## Paso 2: Revisar los archivos que se van a subir

```bash
git status
```

**IMPORTANTE**: Verifica que NO aparezca `.env` en la lista de archivos.

## Paso 3: Agregar todos los archivos

```bash
git add .
```

## Paso 4: Hacer commit

```bash
git commit -m "feat: Initial commit - ERP Voice Chat System for FailFast Hackathon"
```

## Paso 5: Configurar el repositorio remoto

Si aún no has configurado el repositorio remoto:

```bash
git remote add origin https://github.com/Juandavidg123/hackaton-failfast.git
```

Si ya existe, verifica que esté correcto:

```bash
git remote -v
```

## Paso 6: Subir a GitHub

```bash
git push -u origin main
```

Si tu rama principal se llama `master` en lugar de `main`:

```bash
git push -u origin master
```

## Paso 7: Verificar en GitHub

1. Ve a https://github.com/Juandavidg123/hackaton-failfast
2. Verifica que todos los archivos estén ahí
3. **IMPORTANTE**: Verifica que NO esté el archivo `.env`

## Paso 8: Configurar el README en GitHub

GitHub mostrará automáticamente el contenido de `README.md` en la página principal del repositorio.

## Archivos Importantes que SÍ se suben

✅ `.env.example` - Plantilla de configuración (sin credenciales reales)
✅ `README.md` - Documentación principal
✅ `SETUP.md` - Instrucciones de instalación
✅ `QUICK_START.md` - Guía rápida
✅ `CONTRIBUTING.md` - Guía para contribuidores
✅ Todo el código fuente en `src/`
✅ Todos los tests en `tests/`
✅ Scripts en `scripts/`
✅ Migraciones en `migrations/`
✅ Especificaciones en `.kiro/specs/`

## Archivos que NO se suben (están en .gitignore)

❌ `.env` - Contiene tus credenciales
❌ `.venv/` - Entorno virtual de Python
❌ `__pycache__/` - Archivos compilados de Python
❌ `.pytest_cache/` - Cache de pytest
❌ `.hypothesis/` - Cache de Hypothesis
❌ `KMS/` - Logs de LiveKit

## Comandos Útiles

### Ver qué archivos están siendo ignorados
```bash
git status --ignored
```

### Ver el contenido de .gitignore
```bash
cat .gitignore
```

### Deshacer cambios antes de commit
```bash
git restore <archivo>
```

### Ver el historial de commits
```bash
git log --oneline
```

## Solución de Problemas

### Si accidentalmente agregaste .env

```bash
# Remover del staging area
git reset .env

# Asegurarte de que esté en .gitignore
echo ".env" >> .gitignore
```

### Si ya subiste .env a GitHub (¡URGENTE!)

1. **Cambia TODAS tus credenciales inmediatamente**:
   - LiveKit API Key y Secret
   - Supabase URL y Key
   - Deepgram API Key
   - Cartesia API Key

2. Elimina el archivo del historial de Git:
```bash
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

git push origin --force --all
```

3. Contacta a GitHub Support para eliminar el archivo de su cache.

## Siguiente Paso

Una vez subido el código, puedes:
1. Agregar una descripción al repositorio en GitHub
2. Agregar topics/tags: `voice-ai`, `erp`, `livekit`, `python`, `flask`, `hackathon`
3. Crear un README.md atractivo con badges
4. Agregar screenshots o un video demo
5. Compartir el link del repositorio

## Link del Repositorio

https://github.com/Juandavidg123/hackaton-failfast
