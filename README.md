# Pasapalabra

Un juego de *pasapalabra* para dos jugadores por turnos: cada jugador
tiene su propio rosco de 25 letras y su propio reloj, que solo corre
mientras es su turno. Aciertas y sigues; fallas o dices *pasapalabra* y
el turno pasa al rival.

La aplicación es una sola imagen de contenedor sin estado persistente
(FastAPI + HTML/CSS/JS sin build step, sin base de datos), así que corre
igual en Docker local, en Kubernetes o en cualquier plataforma que sepa
ejecutar una imagen OCI.

## Arrancar en local

```
make up      # construye la imagen y levanta el servicio
make wait    # espera a que reporte healthy
```

Luego abre http://127.0.0.1:8080/. `make down` lo para; `make clean`
además borra volúmenes y huérfanos de este proyecto.

## Tres modos de juego

Se elige al crear la partida:

- **Teclado** — cada jugador escribe su respuesta y el servidor la
  compara. Todo ocurre en una sola pantalla; es el modo para jugar entre
  dos personas delante del mismo teclado.
- **Juez** — pensado para competiciones. La pantalla principal es el
  tablero que se proyecta: roscos, relojes, marcador y la pista, sin
  ninguna respuesta. Los jugadores responden en voz alta y un juez, desde
  su propio dispositivo, marca *correcto* o *fallo*.
- **Por categoría** — las preguntas salen de un banco temático en lugar
  del rosco general, y eliges si esa partida se resuelve con teclado o
  con juez. Es una elección sobre *de dónde vienen las preguntas*, no
  otro reglamento: las reglas son las mismas en los tres casos.

Al crear una partida en modo juez, el tablero muestra un enlace del tipo
`http://<host>:8080/juez#<id>:<token>`. Ese enlace es el panel del juez:
es lo único que ve las respuestas y lo único que puede jugar la partida.
Ábrelo en el móvil o el portátil del juez — no lo proyectes. El tablero
se actualiza solo cada segundo con lo que el juez marca.

El token va en el enlace y no se vuelve a mostrar: si se pierde, lo más
rápido es empezar otra partida.

## Generar preguntas de una categoría

```
make rosco CATEGORIA="cine español"
```

Redacta dos roscos del tema con la API de Claude, los somete a las mismas
reglas que los escritos a mano (letras correctas y en orden, sin
repeticiones, sin pistas que filtren su respuesta), pide que se corrija lo
que falle, y escribe `app/data/roscos/<categoría>.json` para que lo revises
y lo commitees.

### Categorías incluidas

Cine Hollywood, Deportes, Marvel Cinematic Universe, DC Comics,
Bridgerton, Pokémon, Videojuegos, Tecnología, DevOps, Películas de
acción, Fórmula 1, Fútbol Argentino, Historia de Argentina, Geografía
Argentina, Geografía de América, Fortnite, Minecraft, y diez roscos de
cultura general al estilo clásico del programa (Pasapalabra Original V1
a V10). Cada categoría trae **al menos dos roscos** —uno por jugador— de
25 preguntas, y algunas traen más: Marvel Cinematic Universe siete, DC
Comics y Deportes seis, Fórmula 1 y Fútbol Argentino cinco. En total, 73
roscos y **1.825 preguntas**, más el rosco general de la portada.

Esto es una herramienta de autoría, no parte del juego: necesita
`ANTHROPIC_API_KEY` en tu `.env` local y vive en una imagen aparte. **La
aplicación desplegada no lleva clave, no sale a internet y no inventa
preguntas durante una partida** ([ADR-0008](docs/decisions/0008-generated-category-roscos.md)).

Lo que la validación comprueba es la forma. Que la respuesta sea *cierta*
no lo comprueba nada: lee el fichero antes de commitearlo.

## Comprobaciones

```
make validate   # config de compose, sintaxis Python, banco de preguntas
make unit       # reglas del juego y contenido
make smoke      # juega un turno contra el stack levantado
```

Todo corre dentro del contenedor: no hace falta Python en la máquina.
Ver [docs/testing.md](docs/testing.md).

## Reglas implementadas

- Rosco de 25 letras (el alfabeto español sin K ni W), con preguntas de
  tipo *empieza por* y *contiene la*.
- Turno alterno: acierto → sigues; fallo o pasapalabra → cambia el turno.
- Reloj por jugador (200 s por defecto). Al agotarse, ese jugador queda
  fuera y el otro sigue jugando solo contra su propio reloj.
- Un jugador puede plantarse y cerrar su rosco antes de tiempo.
- **Pausa**: se pueden parar los dos relojes para un recuento, una
  reclamación o un descanso. Mientras está en pausa no corre el tiempo de
  nadie y no se puede responder ni marcar; el tiempo ya consumido se
  cobra antes de parar, así que pausar nunca regala segundos. En modo
  juez, el botón está en el panel del juez.
- Gana quien tenga más aciertos; a igualdad, menos fallos; si persiste,
  empate. Las soluciones solo se revelan al terminar la partida.
- Las reglas son idénticas en los tres modos: lo único que cambia es
  quién resuelve la letra — el servidor comparando el texto escrito, o
  el juez pulsando un botón — y de qué banco salen las preguntas.
  Pasapalabra y "se planta" también los controla el juez en modo
  competición.

## Mapa del repositorio

| Ruta | Para qué |
|---|---|
| [AGENTS.md](AGENTS.md) / [CLAUDE.md](CLAUDE.md) | El contrato de trabajo — léelo primero. |
| [app/](app/) | La aplicación: reglas, banco de preguntas, API y cliente web. |
| [scripts/](scripts/) | Herramientas de autoría (generador de roscos), fuera del runtime. |
| [tests/](tests/) | Tests de reglas y de contenido. |
| [deploy/k8s/](deploy/k8s/) | Manifiestos genéricos de Kubernetes. |
| [docs/](docs/) | Arquitectura, producto, seguridad, testing, decisiones. |
| [.github/](.github/) | Plantillas de Issue/PR y workflows de CI/CD. |
