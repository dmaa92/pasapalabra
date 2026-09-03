"use strict";

// The judge panel: the only view that ever receives the answers, and in
// judge mode the only one that can play. Both come from the per-match
// token in the URL (`/juez#<id>:<token>`).

const connect = document.getElementById("connect");
const panel = document.getElementById("panel");
const scoreboard = document.getElementById("scoreboard");
const feedback = document.getElementById("feedback");
const buttons = ["ok", "ko", "pass", "resign"].map((id) => document.getElementById(id));

let match = { id: null, token: null };
let state = null;
let syncedAt = 0;
let ticking = null;
let polling = null;
let busy = false;

function seconds() {
  return performance.now() / 1000;
}

async function api(path, options) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `error ${response.status}`);
  return body;
}

function endpoint(suffix) {
  return `/api/games/${match.id}${suffix}?token=${encodeURIComponent(match.token)}`;
}

function say(message, kind) {
  feedback.textContent = message;
  feedback.className = `feedback ${kind || "info"}`;
}

function format(value) {
  const total = Math.ceil(Math.max(0, value));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

function adopt(next) {
  state = next;
  syncedAt = seconds();
  render();
}

async function refresh() {
  if (busy) return;
  busy = true;
  try {
    adopt(await api(endpoint("/judge")));
  } catch (error) {
    say(error.message, "ko");
  } finally {
    busy = false;
  }
}

async function rule(request, message) {
  if (busy || !state || state.over) return;
  busy = true;
  try {
    const payload = await request();
    say(message(payload.result), payload.result.correct === false ? "ko" : "ok");
    // The play response carries the board state, without the answers;
    // ask for the judge's own view again.
    busy = false;
    await refresh();
    return;
  } catch (error) {
    say(error.message, "ko");
    busy = false;
    await refresh();
  }
}

function start() {
  if (ticking) clearInterval(ticking);
  if (polling) clearInterval(polling);
  ticking = setInterval(() => {
    if (!state || state.over || busy) return;
    const player = state.players[state.turn];
    paintClocks(player.remaining_seconds - (seconds() - syncedAt));
  }, 250);
  polling = setInterval(() => {
    if (state && !state.over) refresh();
  }, 1000);
}

function paintClocks(activeLeft) {
  state.players.forEach((player, index) => {
    const node = document.getElementById(`clock-${index}`);
    if (!node) return;
    const left = index === state.turn && activeLeft !== undefined
      ? activeLeft
      : player.remaining_seconds;
    node.textContent = format(left);
  });
}

function render() {
  connect.hidden = true;
  panel.hidden = false;

  scoreboard.innerHTML = "";
  state.players.forEach((player, index) => {
    const box = document.createElement("div");
    box.className = "score-box";
    if (!state.over && index === state.turn) box.classList.add("active");
    if (player.finished) box.classList.add("out");
    const name = document.createElement("strong");
    name.textContent = player.name;
    const clock = document.createElement("span");
    clock.className = "score-clock";
    clock.id = `clock-${index}`;
    clock.textContent = format(player.remaining_seconds);
    const tally = document.createElement("span");
    tally.className = "score-tally";
    tally.textContent = `${player.correct} aciertos · ${player.wrong} fallos · ${player.pending} pendientes`;
    box.append(name, clock, tally);
    scoreboard.appendChild(box);
  });

  const ruling = document.getElementById("ruling");
  if (state.over) {
    buttons.forEach((button) => { button.disabled = true; });
    const [one, two] = state.players;
    document.getElementById("turn-name").textContent = "Partida terminada";
    document.getElementById("clue-letter").textContent = "";
    document.getElementById("clue-text").textContent =
      state.winner === null
        ? `Empate: ${one.correct} - ${two.correct}`
        : `Gana ${state.players[state.winner].name} (${one.correct} - ${two.correct})`;
    document.getElementById("answer").textContent = "—";
    ruling.classList.add("closed");
    drawSheet(0);
    return;
  }

  buttons.forEach((button) => { button.disabled = false; });
  ruling.classList.remove("closed");
  const player = state.players[state.turn];
  document.getElementById("turn-name").textContent = player.name;
  document.getElementById("clue-letter").textContent =
    player.current.kind === "contiene"
      ? `Contiene la ${player.current.letter}:`
      : `Empieza por ${player.current.letter}:`;
  document.getElementById("clue-text").textContent = player.current.clue;
  document.getElementById("answer").textContent = currentAnswer();
  drawSheet(state.turn);
}

function currentAnswer() {
  const letter = state.players[state.turn].current.letter;
  const entry = state.answers[state.turn].find((item) => item.letter === letter);
  return entry ? entry.answer : "";
}

function drawSheet(index) {
  const player = state.players[index];
  document.getElementById("sheet-title").textContent = `Rosco de ${player.name}`;
  const current = player.current ? player.current.letter : null;
  const list = document.createElement("ul");
  list.className = "sheet-list";
  state.answers[index].forEach((entry) => {
    const item = document.createElement("li");
    item.className = entry.status;
    if (entry.letter === current) item.classList.add("current");
    const letter = document.createElement("b");
    letter.textContent = entry.letter;
    const answer = document.createElement("span");
    answer.textContent = entry.answer;
    item.append(letter, answer);
    list.appendChild(item);
  });
  const body = document.getElementById("sheet-body");
  body.innerHTML = "";
  body.appendChild(list);
}

document.getElementById("ok").addEventListener("click", () => rule(
  () => api(endpoint("/judge"), { method: "POST", body: JSON.stringify({ correct: true }) }),
  (result) => `Acierto en la ${result.letter}.`,
));

document.getElementById("ko").addEventListener("click", () => rule(
  () => api(endpoint("/judge"), { method: "POST", body: JSON.stringify({ correct: false }) }),
  (result) => `Fallo en la ${result.letter}: era "${result.solution}".`,
));

document.getElementById("pass").addEventListener("click", () => rule(
  () => api(endpoint("/pass"), { method: "POST" }),
  (result) => `Pasapalabra en la ${result.skipped}.`,
));

document.getElementById("resign").addEventListener("click", () => {
  if (!confirm(`${state.players[state.turn].name} se planta y cierra su rosco?`)) return;
  rule(
    () => api(endpoint("/resign"), { method: "POST" }),
    () => "Rosco cerrado.",
  );
});

document.getElementById("connect-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const id = document.getElementById("game-id").value.trim();
  const token = document.getElementById("token").value.trim();
  if (!id || !token) return;
  location.hash = `${id}:${token}`;
  begin();
});

async function begin() {
  const [id, token] = location.hash.slice(1).split(":");
  if (!id || !token) {
    connect.hidden = false;
    panel.hidden = true;
    return;
  }
  match = { id, token };
  try {
    adopt(await api(endpoint("/judge")));
    start();
  } catch (error) {
    connect.hidden = false;
    panel.hidden = true;
    document.getElementById("game-id").value = id;
    document.getElementById("token").value = token;
    alert(`No se pudo abrir la partida: ${error.message}`);
  }
}

begin();
