(() => {
  const tg = window.Telegram?.WebApp;
  const state = { view: "home", movies: [], selected: null, session: null, query: "", nextOffset: null };
  const $ = (selector) => document.querySelector(selector);
  const grid = $("#movie-grid");
  const loading = $("#loading");
  const empty = $("#empty-state");

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
    if (!response.ok) throw new Error(payload.error || "Something went wrong");
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
    toast.timer = setTimeout(() => element.classList.remove("show"), 2600);
  }

  function setLoading(value) {
    loading.hidden = !value;
    if (value) empty.hidden = true;
  }

  function createCard(movie) {
    const article = document.createElement("article");
    article.className = "movie-card";
    article.tabIndex = 0;
    article.setAttribute("role", "button");
    article.setAttribute("aria-label", `Open ${movie.title}`);
    article.innerHTML = `
      <div class="poster"><span class="poster-letter"></span><span class="quality"></span></div>
      <div class="movie-info"><h3></h3><p></p></div>
      <button class="heart" type="button" aria-label="Toggle favorite">♡</button>`;
    article.querySelector(".poster-letter").textContent = movie.title.slice(0, 1).toUpperCase();
    article.querySelector(".quality").textContent = movie.quality;
    article.querySelector("h3").textContent = movie.title;
    article.querySelector(".movie-info p").textContent = `${movie.type} · ${formatBytes(movie.size)}`;
    const heart = article.querySelector(".heart");
    heart.textContent = movie.favorite ? "♥" : "♡";
    heart.classList.toggle("active", movie.favorite);
    heart.addEventListener("click", (event) => {
      event.stopPropagation();
      toggleFavorite(movie, heart);
    });
    article.addEventListener("click", () => openMovie(movie));
    article.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") openMovie(movie);
    });
    return article;
  }

  function renderMovies(movies, append = false) {
    const cards = movies.map(createCard);
    if (append) grid.append(...cards); else grid.replaceChildren(...cards);
    empty.hidden = state.movies.length > 0;
    $("#result-count").textContent = state.movies.length ? `${state.movies.length} titles` : "";
    $("#load-more").hidden = state.nextOffset === null;
  }

  async function loadMovies(query = "", append = false) {
    setLoading(true);
    try {
      const offset = append && state.nextOffset !== null ? state.nextOffset : 0;
      const result = await api(`/api/movies?q=${encodeURIComponent(query)}&offset=${offset}`);
      state.nextOffset = result.next_offset === "" ? null : Number(result.next_offset);
      state.movies = append ? [...state.movies, ...result.movies] : result.movies;
      renderMovies(result.movies, append);
    } catch (error) {
      state.nextOffset = null;
      renderMovies([]);
      empty.querySelector("h3").textContent = tg?.initData ? "Couldn’t load movies · ရုပ်ရှင်များကို ဖွင့်မရပါ" : "Open inside Telegram · Telegram တွင် ဖွင့်ပါ";
      empty.querySelector("p").textContent = tg?.initData ? error.message : "Launch this Mini App from the FilmX bot. · FilmX bot မှတစ်ဆင့် ဤ Mini App ကို ဖွင့်ပါ။";
    } finally {
      setLoading(false);
    }
  }

  async function loadCollection(kind) {
    setLoading(true);
    try {
      const result = await api(`/api/${kind}`);
      state.nextOffset = null;
      state.movies = result.movies;
      renderMovies(state.movies);
    } catch (error) {
      toast(error.message);
      renderMovies([]);
    } finally {
      setLoading(false);
    }
  }

  async function toggleFavorite(movie, button) {
    try {
      const method = movie.favorite ? "DELETE" : "POST";
      const result = await api(`/api/favorites/${movie.id}`, { method });
      movie.favorite = result.favorite;
      button.textContent = movie.favorite ? "♥" : "♡";
      button.classList.toggle("active", movie.favorite);
      $("#favorite-movie").classList.toggle("active", movie.favorite);
      $("#favorite-movie").textContent = movie.favorite ? "♥" : "♡";
      if (state.view === "favorites" && !movie.favorite) {
        state.movies = state.movies.filter((item) => item.id !== movie.id);
        renderMovies(state.movies);
      }
    } catch (error) { toast(error.message); }
  }

  function openMovie(movie) {
    state.selected = movie;
    $("#detail-title").textContent = movie.title;
    $("#detail-copy").textContent = movie.caption || "Ready for delivery to your Telegram chat. · သင့် Telegram chat သို့ ပို့ရန် အသင့်ဖြစ်ပါပြီ။";
    $("#detail-poster span").textContent = movie.title.slice(0, 2).toUpperCase();
    $("#detail-meta").innerHTML = `<span>${movie.quality}</span><span>${movie.type}</span><span>${formatBytes(movie.size)}</span>`;
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

  function switchView(view) {
    state.view = view;
    document.querySelectorAll(".bottom-nav button").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
    const labels = {
      home: ["DISCOVER", "Latest arrivals"],
      search: ["LIBRARY", "Search movies"],
      favorites: ["YOUR LIST", "Favorites"],
      history: ["WATCH AGAIN", "History"],
    };
    $("#section-kicker").textContent = labels[view][0];
    $("#section-title").textContent = labels[view][1];
    $("#hero").hidden = view !== "home";
    if (view === "search") {
      $("#search-input").focus();
      loadMovies(state.query);
    } else if (view === "favorites" || view === "history") {
      loadCollection(view);
    } else loadMovies();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function initialize() {
    try {
      const config = await api("/api/config");
      $("#app-name").textContent = config.name;
      document.title = config.name;
      if (tg?.initData) {
        state.session = await api("/api/session", { method: "POST" });
        const user = state.session.user;
        $("#avatar").textContent = `${user.first_name?.[0] || "F"}${user.last_name?.[0] || ""}`.toUpperCase();
      }
    } catch (error) { toast(error.message); }
    await loadMovies();
  }

  let searchTimer;
  $("#search-form").addEventListener("submit", (event) => event.preventDefault());
  $("#search-input").addEventListener("input", (event) => {
    state.query = event.target.value.trim();
    $("#search-form").classList.toggle("has-value", Boolean(state.query));
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      if (state.view !== "search") switchView("search"); else loadMovies(state.query);
    }, 280);
  });
  $("#clear-search").addEventListener("click", () => {
    $("#search-input").value = "";
    state.query = "";
    $("#search-form").classList.remove("has-value");
    loadMovies();
  });
  $("#load-more").addEventListener("click", () => loadMovies(state.query, true));
  document.querySelectorAll(".bottom-nav button").forEach((button) => button.addEventListener("click", () => switchView(button.dataset.view)));
  document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => document.getElementById(button.dataset.close).close()));
  $("#get-movie").addEventListener("click", requestMovie);
  $("#check-again").addEventListener("click", checkAgain);
  $("#favorite-movie").addEventListener("click", () => state.selected && toggleFavorite(state.selected, $("#favorite-movie")));
  $("#join-channel").addEventListener("click", (event) => {
    if (tg?.openTelegramLink) { event.preventDefault(); tg.openTelegramLink(event.currentTarget.href); }
  });

  initialize();
})();
