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

    async boot() {
      await Promise.all([this.loadTopics(), this.loadAll(), this.loadDue()]);
    },

    tabClass(name) {
      return (
        "px-3 py-1.5 rounded text-sm " +
        (this.view === name
          ? "bg-indigo-600"
          : "bg-slate-800 hover:bg-slate-700")
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

    async loadDue() {
      const qs = this.topicPath ? `?topic_path=${encodeURIComponent(this.topicPath)}` : "";
      const r = await fetch("/api/cards/due" + qs);
      this.dueCards = await r.json();
      this.currentIdx = 0;
      this.selected = null;
      this.answered = false;
    },

    async selectTopic(path) {
      this.topicPath = path;
      await Promise.all([this.loadAll(), this.loadDue()]);
    },

    pickAnswer(idx) {
      if (this.answered) return;
      this.selected = idx;
      this.answered = true;
    },

    optionClass(idx) {
      if (!this.answered) {
        return "border-slate-700 hover:border-indigo-500 bg-slate-800";
      }
      const correct = this.current.correct_answer;
      if (idx === correct) return "border-emerald-500 bg-emerald-900/30";
      if (idx === this.selected) return "border-rose-500 bg-rose-900/30";
      return "border-slate-700 bg-slate-800 opacity-60";
    },

    async submitReview(difficulty) {
      const card = this.current;
      const correct = this.selected === card.correct_answer;
      await fetch(`/api/cards/${card.id}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ difficulty, correct }),
      });
      this.dueCards.splice(this.currentIdx, 1);
      this.selected = null;
      this.answered = false;
      if (this.currentIdx >= this.dueCards.length) this.currentIdx = 0;
      await this.loadTopics();
    },

    async deleteCard(id) {
      if (!confirm("Excluir este card?")) return;
      await fetch(`/api/cards/${id}`, { method: "DELETE" });
      await Promise.all([this.loadAll(), this.loadDue(), this.loadTopics()]);
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
      await Promise.all([this.loadAll(), this.loadDue(), this.loadTopics()]);
    },

    formatDate(iso) {
      const d = new Date(iso);
      return d.toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        year: "2-digit",
      });
    },
  };
}
