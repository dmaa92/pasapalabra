"use strict";

const setup = document.getElementById("setup");
const judgeLink = document.getElementById("judge-link");
const gameSection = document.getElementById("game");
const turnPanel = document.getElementById("turn-panel");
const resultPanel = document.getElementById("result");
const answerForm = document.getElementById("answer-form");
const waiting = document.getElementById("waiting");
const feedback = document.getElementById("feedback");
const answerInput = document.getElementById("answer");

let state = null;      // last server state
let syncedAt = 0;      // performance.now() when that state arrived
let ticking = null;    // clock interpolation interval
let polling = null;    // judge-mode refresh interval
let busy = false;      // a request is in flight

function seconds() {
  return performance.now() / 1000;
}

async function api(path, options) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(body.detail || `error ${response.status}`);
  }
  return body;
}

function adopt(next) {
  state = next;
  syncedAt = seconds();
  render();
}

function judged() {
  return state && state.mode === "juez";
}

// The server owns the clock; this only interpolates between responses so
// the countdown looks alive, and asks the server to settle it at zero.
function startClocks() {
  stopClocks();
  ticking = setInterval(() => {
    if (!state || state.over || busy) return;
    const player = state.players[state.turn];
    const left = player.remaining_seconds - (seconds() - syncedAt);
    paintClock(state.turn, left);
    if (left <= 0) refresh();
  }, 200);
  // In judge mode this page is only a board: every play happens on the
  // judge panel, so the board has to ask what changed.
  if (judged()) {
    polling = setInterval(() => {
      if (state && !state.over) refresh();
    }, 1000);
  }
}

function stopClocks() {
  if (ticking) clearInterval(ticking);
  if (polling) clearInterval(polling);
  ticking = polling = null;
}

function paintClock(index, value) {
  const panel = document.getElementById(`player-${index}`);
  const left = Math.max(0, value);
  panel.querySelector(".time").textContent = format(left);
  panel.classList.toggle("low", left <= 15 && !state.players[index].finished);
}

function format(value) {
  const total = Math.ceil(value);
  const minutes = Math.floor(total / 60);
  return `${minutes}:${String(total % 60).padStart(2, "0")}`;
}

async function refresh() {
  if (busy) return;
  busy = true;
  try {
    adopt(await api(`/api/games/${state.id}`));
  } catch (error) {
    say(error.message, "ko");
  } finally {
    busy = false;
  }
}

function say(message, kind) {
  feedback.textContent = message;
  feedback.className = `feedback ${kind || "info"}`;
}

function drawRosco(panel, player) {
  const wheel = panel.querySelector(".rosco");
  const radius = 108;
  const current = player.current ? player.current.letter : null;
  wheel.innerHTML = "";
  player.letters.forEach((entry, index) => {
    const angle = (index / player.letters.length) * 2 * Math.PI - Math.PI / 2;
    const node = document.createElement("span");
    node.className = `letter ${entry.status}`;
    if (entry.letter === current) node.classList.add("current");
    node.textContent = entry.letter;
    node.style.transform =
      `translate(${Math.cos(angle) * radius}px, ${Math.sin(angle) * radius}px)`;
    wheel.appendChild(node);
  });
}

function render() {
  setup.hidden = true;
  gameSection.hidden = false;

  state.players.forEach((player, index) => {
    const panel = document.getElementById(`player-${index}`);
    panel.querySelector(".player-name").textContent = player.name;
    panel.querySelector(".score").textContent =
      `${player.correct} aciertos · ${player.wrong} fallos · ${player.pending} pendientes` +
      (player.finished ? ` · ${player.finish_reason === "timeout" ? "sin tiempo" : "rosco cerrado"}` : "");
    panel.classList.toggle("active", !state.over && index === state.turn);
    panel.classList.toggle("out", player.finished);
    paintClock(index, player.remaining_seconds);
    drawRosco(panel, player);
  });

  if (state.over) {
    turnPanel.hidden = true;
    showResult();
    return;
  }

  turnPanel.hidden = false;
  resultPanel.hidden = true;
  answerForm.hidden = judged();
  waiting.hidden = !judged();

  const player = state.players[state.turn];
  document.getElementById("turn-name").textContent = player.name;
  document.getElementById("clue-letter").textContent =
    player.current.kind === "contiene"
      ? `Contiene la ${player.current.letter}:`
      : `Empieza por ${player.current.letter}:`;
  document.getElementById("clue-text").textContent = player.current.clue;
  if (!judged()) {
    answerInput.value = "";
    answerInput.focus();
  }
}

function showResult() {
  resultPanel.hidden = false;
  const [one, two] = state.players;
  document.getElementById("result-title").textContent =
    state.winner === null
      ? `Empate: ${one.correct} - ${two.correct}`
      : `Gana ${state.players[state.winner].name} (${one.correct} - ${two.correct})`;

  const grid = document.createElement("div");
  grid.className = "solutions-grid";
  state.solutions.forEach((solution, index) => {
    const column = document.createElement("div");
    const title = document.createElement("h3");
    title.textContent = state.players[index].name;
    const list = document.createElement("ul");
    solution.forEach((entry) => {
      const item = document.createElement("li");
      item.className = entry.status;
      const letter = document.createElement("b");
      letter.textContent = entry.letter;
      const answer = document.createElement("span");
      answer.textContent = entry.answer;
      item.append(letter, answer);
      list.appendChild(item);
    });
    column.append(title, list);
    grid.appendChild(column);
  });
  const solutions = document.getElementById("solutions");
  solutions.innerHTML = "";
  solutions.appendChild(grid);
}

async function play(request, onResult) {
  if (busy || !state || state.over) return;
  busy = true;
  try {
    const payload = await request();
    onResult(payload.result, payload.game);
    adopt(payload.game);
  } catch (error) {
    say(error.message, "ko");
    try {
      adopt(await api(`/api/games/${state.id}`));
    } catch (_) {
      /* keep showing the last known state */
    }
  } finally {
    busy = false;
  }
}

function showJudgeLink(game) {
  const url = `${location.origin}/juez#${game.id}:${game.judge_token}`;
  const anchor = document.getElementById("judge-url");
  anchor.textContent = url;
  anchor.href = url;
  judgeLink.hidden = false;
  document.getElementById("copy-judge").onclick = async () => {
    try {
      await navigator.clipboard.writeText(url);
      say("Enlace del juez copiado.", "ok");
    } catch (_) {
      say("Copia el enlace a mano: el navegador no lo permitio.", "info");
    }
  };
  document.getElementById("open-judge").onclick = () => window.open(url, "_blank");
}

document.getElementById("setup-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const game = await api("/api/games", {
      method: "POST",
      body: JSON.stringify({
        player_one: document.getElementById("player-one").value,
        player_two: document.getElementById("player-two").value,
        seconds: Number(document.getElementById("seconds").value),
        mode: document.getElementById("mode").value,
      }),
    });
    location.hash = game.id;
    if (game.judge_token) showJudgeLink(game);
    adopt(game);
    say("");
    startClocks();
  } catch (error) {
    say(error.message, "ko");
  }
});

answerForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = answerInput.value.trim();
  if (!text) return;
  play(
    () => api(`/api/games/${state.id}/answer`, {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
    (result) => {
      if (result.correct) {
        say(`Correcto: ${result.letter}`, "ok");
      } else {
        say(`Fallo en la ${result.letter}: era "${result.solution}"`, "ko");
      }
    },
  );
});

document.getElementById("pass").addEventListener("click", () => {
  play(
    () => api(`/api/games/${state.id}/pass`, { method: "POST" }),
    (result) => say(`Pasapalabra en la ${result.skipped}`, "info"),
  );
});

document.getElementById("resign").addEventListener("click", () => {
  const name = state.players[state.turn].name;
  if (!confirm(`${name}, te plantas y cierras tu rosco?`)) return;
  play(
    () => api(`/api/games/${state.id}/resign`, { method: "POST" }),
    () => say(`${name} se planta.`, "info"),
  );
});

document.getElementById("restart").addEventListener("click", () => {
  stopClocks();
  state = null;
  location.hash = "";
  gameSection.hidden = true;
  resultPanel.hidden = true;
  judgeLink.hidden = true;
  setup.hidden = false;
  say("");
});

// Reopening the board with a match id in the URL (a projector that got
// refreshed, or a second screen) picks the match back up.
(async function resume() {
  const id = location.hash.slice(1);
  if (!id) return;
  try {
    adopt(await api(`/api/games/${id}`));
    startClocks();
  } catch (_) {
    location.hash = "";
  }
})();
