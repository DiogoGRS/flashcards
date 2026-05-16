function flashApp() {
  return {
    view: "review",
    topicPath: null,
    topics: {},
    allCards: [],
    dueCards: [],
    currentIdx: 0,
    selected: null,
    answered: false,

    // Session tracking
    sessionStarted: false,
    sessionDone: false,
    sessionLimit: 20,
    dueTotal: 0,
    sessionStats: { total: 0, correct: 0, wrong: 0 },

    // Edit modal
    editCard: null,
    editForm: { topicsRaw: "", question: "", options: [], correct_answer: 0, explanation: "" },
    editError: "",

    // Stats
    stats: null,

    // Create form
    form: {
      topicsRaw: "",
      question: "",
      options: ["", ""],
      correct_answer: 0,
      explanation: "",
    },
    formError: "",

    get current() {
      return this.dueCards[this.currentIdx] || null;
    },

    get cardPosition() {
      if (!this.sessionStats.total) return 1;
      return this.sessionStats.total - this.dueCards.length + 1;
    },

    get progressPercent() {
      if (!this.sessionStats.total) return 0;
      const done = this.sessionStats.total - this.dueCards.length;
      return Math.round((done / this.sessionStats.total) * 100);
    },

    async boot() {
      const renderer = new marked.Renderer();
      renderer.code = function (code, lang) {
        const language = lang && hljs.getLanguage(lang) ? lang : "plaintext";
        const highlighted = hljs.highlight(code, { language }).value;
        return `<pre><code class="hljs language-${language}">${highlighted}</code></pre>`;
      };
      marked.setOptions({ renderer, breaks: true, gfm: true });

      await Promise.all([this.loadTopics(), this.loadAll(), this.loadDueCounts()]);
      this.initKeyboard();
    },

    renderMd(text) {
      if (!text) return "";
      return marked.parse(text);
    },

    renderMdInline(text) {
      if (!text) return "";
      return marked.parseInline(text);
    },

    initKeyboard() {
      document.addEventListener("keydown", (e) => {
        if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
        if (this.editCard) return;

        if (this.view === "review" && this.current) {
          if (!this.answered) {
            const num = parseInt(e.key);
            if (num >= 1 && num <= (this.current.options || []).length) {
              this.pickAnswer(num - 1);
            }
          } else {
            if (e.key === "e" || e.key === "E") this.submitReview("easy");
            if (e.key === "m" || e.key === "M") this.submitReview("medium");
            if (e.key === "d" || e.key === "D") this.submitReview("hard");
          }
        }
      });
    },

    tabClass(name) {
      return (
        "px-3 py-1.5 rounded text-sm " +
        (this.view === name ? "bg-indigo-600" : "bg-slate-800 hover:bg-slate-700")
      );
    },

    async loadTopics() {
      const r = await fetch("/api/topics");
      this.topics = await r.json();
    },

    async loadAll() {
      const qs = this.topicPath ? `?topic_path=${encodeURIComponent(this.topicPath)}` : "";
      const r = await fetch("/api/cards" + qs);
      this.allCards = await r.json();
    },

    async loadDueCounts() {
      const qs = this.topicPath ? `?topic_path=${encodeURIComponent(this.topicPath)}` : "";
      const r = await fetch("/api/cards/due" + qs);
      const cards = await r.json();
      this.dueTotal = cards.length;
    },

    async startSession() {
      const qs = this.topicPath ? `?topic_path=${encodeURIComponent(this.topicPath)}` : "";
      const r = await fetch("/api/cards/due" + qs);
      const cards = await r.json();
      this.dueCards = cards.slice(0, this.sessionLimit);
      this.currentIdx = 0;
      this.selected = null;
      this.answered = false;
      this.sessionDone = false;
      this.sessionStarted = true;
      this.sessionStats = { total: this.dueCards.length, correct: 0, wrong: 0 };
    },

    async selectTopic(path) {
      this.topicPath = path;
      this.sessionDone = false;
      this.sessionStarted = false;
      await Promise.all([this.loadAll(), this.loadDueCounts()]);
    },

    pickAnswer(idx) {
      if (this.answered) return;
      this.selected = idx;
      this.answered = true;
    },

    optionClass(idx) {
      if (!this.answered || !this.current) {
        return "border-slate-700 hover:border-indigo-500 bg-slate-800";
      }
      const correct = this.current.correct_answer;
      if (idx === correct) return "border-emerald-500 bg-emerald-900/30";
      if (idx === this.selected) return "border-rose-500 bg-rose-900/30";
      return "border-slate-700 bg-slate-800 opacity-60";
    },

    async submitReview(difficulty) {
      if (!this.answered) return;
      const card = this.current;
      if (!card) return;
      const correct = this.selected === card.correct_answer;

      // Advance UI synchronously so a rapid second click can't re-enter
      // this handler for the same card.
      this.answered = false;
      this.selected = null;
      this.dueCards.splice(this.currentIdx, 1);

      if (correct) {
        this.sessionStats.correct++;
      } else {
        this.sessionStats.wrong++;
      }

      if (this.dueCards.length === 0) {
        this.sessionDone = true;
      } else if (this.currentIdx >= this.dueCards.length) {
        this.currentIdx = 0;
      }

      await fetch(`/api/cards/${card.id}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ difficulty, correct }),
      });

      await this.loadTopics();
    },

    async restartSession() {
      this.sessionDone = false;
      this.sessionStarted = false;
      this.dueCards = [];
      await this.loadDueCounts();
    },

    async deleteCard(id) {
      if (!confirm("Excluir este card?")) return;
      await fetch(`/api/cards/${id}`, { method: "DELETE" });
      await Promise.all([this.loadAll(), this.loadDueCounts(), this.loadTopics()]);
    },

    async deleteFromReview() {
      if (!confirm("Excluir este card?")) return;
      const card = this.current;
      await fetch(`/api/cards/${card.id}`, { method: "DELETE" });
      this.dueCards.splice(this.currentIdx, 1);
      this.sessionStats.total--;
      this.dueTotal = Math.max(0, this.dueTotal - 1);
      this.selected = null;
      this.answered = false;
      if (this.dueCards.length === 0) {
        this.sessionDone = true;
      } else if (this.currentIdx >= this.dueCards.length) {
        this.currentIdx = 0;
      }
      await Promise.all([this.loadAll(), this.loadTopics()]);
    },

    openEdit(card) {
      this.editCard = card;
      this.editError = "";
      this.editForm = {
        topicsRaw: (card.topics || []).join("/"),
        question: card.question,
        options: [...card.options],
        correct_answer: card.correct_answer,
        explanation: card.explanation || "",
      };
    },

    async submitEdit() {
      this.editError = "";
      const topics = this.editForm.topicsRaw
        .split("/")
        .map((s) => s.trim())
        .filter(Boolean);
      const options = this.editForm.options.map((o) => o.trim()).filter(Boolean);

      if (!this.editForm.question.trim()) {
        this.editError = "pergunta obrigatória";
        return;
      }
      if (options.length < 2) {
        this.editError = "mínimo 2 opções";
        return;
      }
      if (this.editForm.correct_answer >= options.length) {
        this.editError = "marque qual opção é a correta";
        return;
      }

      const r = await fetch(`/api/cards/${this.editCard.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topics,
          question: this.editForm.question.trim(),
          options,
          correct_answer: this.editForm.correct_answer,
          explanation: this.editForm.explanation.trim() || null,
        }),
      });

      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        this.editError = err.detail || "erro ao salvar";
        return;
      }

      this.editCard = null;
      await Promise.all([this.loadAll(), this.loadTopics()]);
    },

    async loadStats() {
      const r = await fetch("/api/stats");
      this.stats = await r.json();
    },

    async exportCards() {
      const r = await fetch("/api/export");
      const data = await r.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const date = new Date().toISOString().split("T")[0];
      a.download = `flashcards-snapshot-${date}.json`;
      a.click();
      URL.revokeObjectURL(url);
    },

    resetForm() {
      this.form = {
        topicsRaw: "",
        question: "",
        options: ["", ""],
        correct_answer: 0,
        explanation: "",
      };
      this.formError = "";
    },

    async submitNew() {
      this.formError = "";
      const topics = this.form.topicsRaw
        .split("/")
        .map((s) => s.trim())
        .filter(Boolean);
      const options = this.form.options.map((o) => o.trim()).filter(Boolean);

      if (!this.form.question.trim()) {
        this.formError = "pergunta obrigatória";
        return;
      }
      if (options.length < 2) {
        this.formError = "mínimo 2 opções";
        return;
      }
      if (this.form.correct_answer >= options.length) {
        this.formError = "marque qual opção é a correta";
        return;
      }

      const r = await fetch("/api/cards", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          topics,
          question: this.form.question.trim(),
          options,
          correct_answer: this.form.correct_answer,
          explanation: this.form.explanation.trim() || null,
        }),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        this.formError = err.detail?.[0]?.msg || err.detail || "erro ao criar";
        return;
      }
      this.resetForm();
      this.view = "browse";
      await Promise.all([this.loadAll(), this.loadDueCounts(), this.loadTopics()]);
    },

    formatDate(iso) {
      const d = new Date(iso);
      return d.toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        year: "2-digit",
      });
    },

    easeColor(ef) {
      if (ef >= 2.5) return "text-emerald-400";
      if (ef >= 2.0) return "text-amber-400";
      return "text-rose-400";
    },
  };
}
