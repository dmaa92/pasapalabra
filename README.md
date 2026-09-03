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

## Dos modos de juego

Se elige al crear la partida:

- **Teclado** — cada jugador escribe su respuesta y el servidor la
  compara. Todo ocurre en una sola pantalla; es el modo para jugar entre
  dos personas delante del mismo teclado.
- **Juez** — pensado para competiciones. La pantalla principal es el
  tablero que se proyecta: roscos, relojes, marcador y la pista, sin
  ninguna respuesta. Los jugadores responden en voz alta y un juez, desde
  su propio dispositivo, marca *correcto* o *fallo*.

Al crear una partida en modo juez, el tablero muestra un enlace del tipo
`http://<host>:8080/juez#<id>:<token>`. Ese enlace es el panel del juez:
es lo único que ve las respuestas y lo único que puede jugar la partida.
Ábrelo en el móvil o el portátil del juez — no lo proyectes. El tablero
se actualiza solo cada segundo con lo que el juez marca.

El token va en el enlace y no se vuelve a mostrar: si se pierde, lo más
rápido es empezar otra partida.

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
- Gana quien tenga más aciertos; a igualdad, menos fallos; si persiste,
  empate. Las soluciones solo se revelan al terminar la partida.
- Las reglas son idénticas en los dos modos: lo único que cambia es
  quién resuelve la letra — el servidor comparando el texto escrito, o
  el juez pulsando un botón. Pasapalabra y "se planta" también los
  controla el juez en modo competición.

## Mapa del repositorio

| Ruta | Para qué |
|---|---|
| [AGENTS.md](AGENTS.md) / [CLAUDE.md](CLAUDE.md) | El contrato de trabajo — léelo primero. |
| [app/](app/) | La aplicación: reglas, banco de preguntas, API y cliente web. |
| [tests/](tests/) | Tests de reglas y de contenido. |
| [deploy/k8s/](deploy/k8s/) | Manifiestos genéricos de Kubernetes. |
| [docs/](docs/) | Arquitectura, producto, seguridad, testing, decisiones. |
| [.github/](.github/) | Plantillas de Issue/PR y workflows de CI/CD. |
