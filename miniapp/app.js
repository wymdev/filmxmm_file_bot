(() => {
  "use strict";

  const tg = window.Telegram?.WebApp;
  const state = {
    view: "home",
    movies: [],
    selected: null,
    session: null,
    query: "",
    quality: "",
    type: "",
    nextOffset: null,
    total: 0,
    loading: false,
    controller: null,
  };
  const cache = new Map();
  const $ = (selector) => document.querySelector(selector);
  const grid = $("#movie-grid");
  const loading = $("#loading");
  const empty = $("#empty-state");
  const library = $("#library");

  tg?.ready();
  tg?.expand();
  tg?.setHeaderColor?.("secondary_bg_color");
  tg?.setBackgroundColor?.("bg_color");

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    if (tg?.initData) headers.set("Authorization", `tma ${tg.initData}`);
    if (options.body) headers.set("Content-Type", "application/json");
    const response = await fetch(path, { ...options, headers });
    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("json") ? await response.json() : { error: await response.text() };
    if (!response.ok) throw new Error(payload.error || "Something went wrong · တစ်ခုခုမှားယွင်းနေပါသည်");
    return payload;
  }

  function formatBytes(bytes) {
    if (!bytes) return "File";
    const units = ["B", "KB", "MB", "GB"];
    const level = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    return `${(bytes / (1024 ** level)).toFixed(level > 1 ? 1 : 0)} ${units[level]}`;
  }

  function toast(message) {
    const element = $("#toast");
    element.textContent = message;
    element.classList.add("show");
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => element.classList.remove("show"), 2800);
  }

  function setLoading(value, append = false) {
    state.loading = value;
    library.setAttribute("aria-busy", String(value));
    loading.hidden = !value || append;
    $("#load-more").disabled = value;
    if (value && !append) empty.hidden = true;
  }

  function setSearchStatus() {
    const status = $("#search-status");
    const active = state.query || state.quality || state.type;
    status.hidden = !active;
    if (active) {
      const filters = [state.quality, state.type].filter(Boolean).join(" · ");
      status.textContent = `${state.total} result${state.total === 1 ? "" : "s"}${filters ? ` · ${filters}` : ""}`;
    }
  }

  function createCard(movie) {
    const article = document.createElement("article");
    article.className = "group relative min-w-0 cursor-pointer";
    article.tabIndex = 0;
    article.setAttribute("role", "button");
    article.setAttribute("aria-label", `Open ${movie.title}`);
    article.innerHTML = `
      <div class="poster-art flex aspect-[2/2.85] items-end rounded-2xl p-3 transition duration-300 group-hover:-translate-y-1 group-hover:shadow-float">
        <span class="poster-letter relative z-10 font-display text-5xl italic leading-none text-accent/80"></span>
        <span class="quality absolute bottom-2.5 right-2.5 z-10 rounded-md bg-app/75 px-1.5 py-1 text-[8px] font-bold uppercase tracking-wider text-ink backdrop-blur"></span>
      </div>
      <div class="pt-2.5 pr-7">
        <h3 class="truncate text-xs font-semibold leading-5 text-ink"></h3>
        <p class="m-0 truncate text-[9px] uppercase tracking-wide text-subtle"></p>
      </div>
      <button class="heart absolute bottom-1.5 right-0 grid size-7 place-items-center text-xl text-subtle transition hover:text-accent" type="button" aria-label="Toggle favorite">♡</button>`;
    article.querySelector(".poster-letter").textContent = movie.title.slice(0, 1).toUpperCase();
    article.querySelector(".quality").textContent = movie.quality;
    article.querySelector("h3").textContent = movie.title;
    article.querySelector("p").textContent = `${movie.type} · ${formatBytes(movie.size)}`;
    const heart = article.querySelector(".heart");
    heart.textContent = movie.favorite ? "♥" : "♡";
    heart.classList.toggle("text-accent", movie.favorite);
    heart.addEventListener("click", (event) => {
      event.stopPropagation();
      toggleFavorite(movie, heart);
    });
    article.addEventListener("click", () => openMovie(movie));
    article.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openMovie(movie);
      }
    });
    return article;
  }

  function renderMovies(movies, append = false) {
    const cards = movies.map(createCard);
    if (append) grid.append(...cards); else grid.replaceChildren(...cards);
    empty.hidden = state.movies.length > 0;
    $("#result-count").textContent = state.total ? `${state.movies.length} / ${state.total}` : "";
    $("#library-total").textContent = state.total ? `${state.total} movies` : "Movie library";
    $("#load-more").hidden = state.nextOffset === null;
    setSearchStatus();
  }

  function movieRequestUrl(offset) {
    const params = new URLSearchParams({ q: state.query, offset: String(offset) });
    if (state.quality) params.set("quality", state.quality);
    if (state.type) params.set("type", state.type);
    return `/api/movies?${params}`;
  }

  function remember(key, value) {
    cache.set(key, value);
    if (cache.size > 20) cache.delete(cache.keys().next().value);
  }

  async function loadMovies(append = false) {
    if (state.loading && append) return;
    const offset = append && state.nextOffset !== null ? state.nextOffset : 0;
    const url = movieRequestUrl(offset);
    state.controller?.abort();
    const controller = new AbortController();
    state.controller = controller;
    setLoading(true, append);
    try {
      let result = cache.get(url);
      if (!result) {
        result = await api(url, { signal: controller.signal });
        remember(url, result);
      }
      state.nextOffset = result.next_offset === "" ? null : Number(result.next_offset);
      state.total = Number(result.total || 0);
      state.movies = append ? [...state.movies, ...result.movies] : result.movies;
      renderMovies(result.movies, append);
    } catch (error) {
      if (error.name === "AbortError") return;
      if (!append) {
        state.movies = [];
        state.total = 0;
        state.nextOffset = null;
        renderMovies([]);
        empty.querySelector("h3").textContent = tg?.initData ? "Couldn’t load movies · ရုပ်ရှင်များကို ဖွင့်မရပါ" : "Open inside Telegram · Telegram တွင် ဖွင့်ပါ";
        empty.querySelector("p").textContent = tg?.initData ? error.message : "Launch this Mini App from the FilmX bot. · FilmX bot မှတစ်ဆင့် ဤ Mini App ကို ဖွင့်ပါ။";
      } else toast(error.message);
    } finally {
      if (state.controller === controller) setLoading(false, append);
    }
  }

  async function loadCollection(kind) {
    state.controller?.abort();
    const controller = new AbortController();
    state.controller = controller;
    setLoading(true);
    try {
      const result = await api(`/api/${kind}`, { signal: controller.signal });
      state.nextOffset = null;
      state.movies = result.movies;
      state.total = result.movies.length;
      renderMovies(state.movies);
    } catch (error) {
      if (error.name === "AbortError") return;
      state.movies = [];
      state.total = 0;
      toast(error.message);
      renderMovies([]);
    } finally {
      if (state.controller === controller) setLoading(false);
    }
  }

  async function toggleFavorite(movie, button) {
    try {
      const method = movie.favorite ? "DELETE" : "POST";
      const result = await api(`/api/favorites/${movie.id}`, { method });
      movie.favorite = result.favorite;
      cache.clear();
      button.textContent = movie.favorite ? "♥" : "♡";
      button.classList.toggle("text-accent", movie.favorite);
      $("#favorite-movie").classList.toggle("active", movie.favorite);
      $("#favorite-movie").textContent = movie.favorite ? "♥" : "♡";
      if (state.view === "favorites" && !movie.favorite) {
        state.movies = state.movies.filter((item) => item.id !== movie.id);
        state.total = state.movies.length;
        renderMovies(state.movies);
      }
    } catch (error) { toast(error.message); }
  }

  function openMovie(movie) {
    state.selected = movie;
    $("#detail-title").textContent = movie.title;
    $("#detail-copy").textContent = movie.caption || "Ready for delivery to your Telegram chat. · သင့် Telegram chat သို့ ပို့ရန် အသင့်ဖြစ်ပါပြီ။";
    $("#detail-poster span").textContent = movie.title.slice(0, 2).toUpperCase();
    const metadata = [movie.quality, movie.type, formatBytes(movie.size)];
    $("#detail-meta").replaceChildren(...metadata.map((value) => {
      const tag = document.createElement("span");
      tag.className = "rounded-full border border-line px-2.5 py-1 text-[9px] uppercase text-subtle";
      tag.textContent = value;
      return tag;
    }));
    $("#favorite-movie").textContent = movie.favorite ? "♥" : "♡";
    $("#favorite-movie").classList.toggle("active", movie.favorite);
    $("#movie-sheet").showModal();
  }

  async function requestMovie() {
    if (!state.selected) return;
    const button = $("#get-movie");
    button.disabled = true;
    button.firstChild.textContent = "Checking · စစ်ဆေးနေသည် ";
    try {
      const result = await api(`/api/movies/${state.selected.id}/request`, { method: "POST" });
      if (result.status === "join_required") {
        $("#join-channel").href = result.join_url;
        $("#movie-sheet").close();
        $("#join-dialog").showModal();
      } else {
        $("#movie-sheet").close();
        toast("Movie sent — check your bot chat · ရုပ်ရှင်ပို့ပြီးပါပြီ — bot chat ကို စစ်ဆေးပါ");
        tg?.HapticFeedback?.notificationOccurred("success");
      }
    } catch (error) { toast(error.message); }
    finally {
      button.disabled = false;
      button.firstChild.textContent = "Get movie · ရုပ်ရှင်ရယူရန် ";
    }
  }

  async function checkAgain() {
    const button = $("#check-again");
    button.disabled = true;
    button.textContent = "Checking… · စစ်ဆေးနေသည်…";
    try {
      const result = await api(`/api/movies/${state.selected.id}/request`, { method: "POST" });
      if (result.status === "join_required") {
        tg?.HapticFeedback?.notificationOccurred("error");
        toast("Please join the channel first · ကျေးဇူးပြု၍ ချန်နယ်သို့ အရင်ဝင်ပါ");
      } else {
        $("#join-dialog").close();
        toast("Verified — your movie is on the way · အတည်ပြုပြီးပါပြီ — ရုပ်ရှင်ပို့နေပါသည်");
        tg?.HapticFeedback?.notificationOccurred("success");
      }
    } catch (error) { toast(error.message); }
    finally { button.disabled = false; button.textContent = "Check again · ပြန်စစ်ရန်"; }
  }

  function setViewLabels(view) {
    const labels = {
      home: ["DISCOVER", "Latest arrivals"],
      search: ["SMART SEARCH", "Search results"],
      favorites: ["YOUR LIST", "Favorites"],
      history: ["WATCH AGAIN", "History"],
    };
    $("#section-kicker").textContent = labels[view][0];
    $("#section-title").textContent = labels[view][1];
  }

  function switchView(view) {
    state.view = view;
    document.querySelectorAll(".nav-button").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
    setViewLabels(view);
    $("#hero").hidden = view !== "home";
    if (view === "search") {
      $("#search-input").focus();
      loadMovies();
    } else if (view === "favorites" || view === "history") {
      loadCollection(view);
    } else {
      state.query = "";
      state.quality = "";
      state.type = "";
      $("#search-input").value = "";
      $("#type-filter").value = "";
      document.querySelectorAll("[data-quality]").forEach((item) => item.setAttribute("aria-pressed", String(item.dataset.quality === "")));
      loadMovies();
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function initialize() {
    const configRequest = api("/api/config");
    const sessionRequest = tg?.initData ? api("/api/session", { method: "POST" }) : Promise.resolve(null);
    const [configResult, sessionResult] = await Promise.allSettled([configRequest, sessionRequest]);
    if (configResult.status === "fulfilled") {
      $("#app-name").textContent = configResult.value.name;
      document.title = configResult.value.name;
    }
    if (sessionResult.status === "fulfilled" && sessionResult.value) {
      state.session = sessionResult.value;
      const user = state.session.user;
      $("#avatar").textContent = `${user.first_name?.[0] || "F"}${user.last_name?.[0] || ""}`.toUpperCase();
    }
    await loadMovies();
  }

  let searchTimer;
  $("#search-form").addEventListener("submit", (event) => {
    event.preventDefault();
    clearTimeout(searchTimer);
    state.query = $("#search-input").value.trim();
    if (state.view !== "search") switchView("search"); else loadMovies();
  });
  $("#search-input").addEventListener("input", (event) => {
    state.query = event.target.value.trim();
    $("#clear-search").classList.toggle("hidden", !state.query);
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      if (state.view !== "search") switchView("search"); else loadMovies();
    }, 220);
  });
  $("#clear-search").addEventListener("click", () => {
    $("#search-input").value = "";
    state.query = "";
    $("#clear-search").classList.add("hidden");
    loadMovies();
  });
  $("#quality-filters").addEventListener("click", (event) => {
    const button = event.target.closest("[data-quality]");
    if (!button) return;
    state.quality = button.dataset.quality;
    document.querySelectorAll("[data-quality]").forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
    if (state.view !== "search") switchView("search"); else loadMovies();
  });
  $("#type-filter").addEventListener("change", (event) => {
    state.type = event.target.value;
    if (state.view !== "search") switchView("search"); else loadMovies();
  });
  $("#load-more").addEventListener("click", () => loadMovies(true));
  document.querySelectorAll(".nav-button").forEach((button) => button.addEventListener("click", () => switchView(button.dataset.view)));
  document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => document.getElementById(button.dataset.close).close()));
  $("#get-movie").addEventListener("click", requestMovie);
  $("#check-again").addEventListener("click", checkAgain);
  $("#favorite-movie").addEventListener("click", () => state.selected && toggleFavorite(state.selected, $("#favorite-movie")));
  $("#join-channel").addEventListener("click", (event) => {
    if (tg?.openTelegramLink) { event.preventDefault(); tg.openTelegramLink(event.currentTarget.href); }
  });

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && !$("#load-more").hidden && !state.loading) loadMovies(true);
    }, { rootMargin: "160px" });
    observer.observe($("#load-more"));
  }

  initialize();
})();
