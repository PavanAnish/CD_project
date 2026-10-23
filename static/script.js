(() => {
	const sourceEditor   = document.querySelector("#source-code");
	const compileButton  = document.querySelector("#compile-button");
	const resetButton    = document.querySelector("#reset-button");
	const statusPill     = document.querySelector("#status-pill");
	const resultsPanel   = document.querySelector(".results-panel");
	const lineCount      = document.querySelector("#line-count");
	const tabOutput      = document.querySelector("#tab-output");
	const tabGrammar     = document.querySelector("#tab-grammar");
	const btnOutput      = document.querySelector("#btn-output");
	const btnGrammar     = document.querySelector("#btn-grammar");
	const initialSource  = sourceEditor.value;

	// ── Tab switching ────────────────────────────────────────────────────────
	function activateTab(tab, btn) {
		[tabOutput, tabGrammar].forEach(t => t.classList.add("hidden"));
		[btnOutput, btnGrammar].forEach(b => { b.classList.remove("active"); b.setAttribute("aria-selected", "false"); });
		tab.classList.remove("hidden");
		btn.classList.add("active");
		btn.setAttribute("aria-selected", "true");
	}
	btnOutput.addEventListener("click",  () => activateTab(tabOutput,  btnOutput));
	btnGrammar.addEventListener("click", () => activateTab(tabGrammar, btnGrammar));

	// ── Utilities ────────────────────────────────────────────────────────────
	function updateLineCount() {
		const lines = sourceEditor.value.split("\n").length;
		lineCount.textContent = `${lines} ${lines === 1 ? "LINE" : "LINES"}`;
	}

	function escapeHtml(value) {
		return String(value).replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]);
	}

	function setStatus(label, state) {
		statusPill.textContent = label;
		statusPill.className = `status-pill ${state}`;
	}

	// ── Pipeline stage indicators ────────────────────────────────────────────
	const STAGE_IDS = { lexical: "stage-lexical", syntax: "stage-syntax", semantic: "stage-semantic" };

	function resetStages() {
		Object.values(STAGE_IDS).forEach(id => {
			const el = document.getElementById(id);
			if (el) { el.className = "stage"; el.removeAttribute("title"); }
		});
	}

	function updateStages(pipeline) {
		if (!Array.isArray(pipeline)) return;
		pipeline.forEach(({ phase, status, detail }) => {
			const el = document.getElementById(STAGE_IDS[phase]);
			if (!el) return;
			el.className = `stage stage-${status}`;
			el.title = detail || "";
		});
	}

	// ── Render helpers ───────────────────────────────────────────────────────
	function renderFailure(result) {
		const error = result?.error || {};
		const phase = error?.phase || result?.phase || "request";
		const hasLoc = Number.isInteger(error?.line);
		const location = hasLoc ? `Line ${error.line}, column ${error.column}` : "Request error";

		// Show all semantic errors if present
		let extraErrors = "";
		if (Array.isArray(result?.semantic_errors) && result.semantic_errors.length > 1) {
			const list = result.semantic_errors
				.map(e => {
					const loc = e.line != null ? `<small>Line ${e.line}${e.column != null ? `, col ${e.column}` : ""}</small>` : "";
					return `<li>${escapeHtml(e.message)}${loc}</li>`;
				}).join("");
			extraErrors = `<ul class="error-list">${list}</ul>`;
		}

		tabOutput.innerHTML =
			`<div class="diagnostic"><b>${escapeHtml(phase)} error</b>${escapeHtml(error?.message || "Compilation failed.")}<small>${escapeHtml(location)}</small></div>` +
			extraErrors;

		// If we have tokens/AST even on error, show them collapsed
		if (result?.tokens) {
			tabOutput.innerHTML += partialResultHTML(result);
		}

		setStatus("ERROR", "error");
	}

	function partialResultHTML(result) {
		let html = "";
		if (result.tokens) {
			const tokens = result.tokens.map(tok =>
				`<span class="token"><b>${escapeHtml(tok.type)}</b> ${escapeHtml(tok.value)}</span>`
			).join("");
			html += `<section class="result-section"><h3>TOKEN STREAM</h3><div class="token-list">${tokens || "<span class='token'>EMPTY</span>"}</div></section>`;
		}
		if (result.ast) {
			const ast = JSON.stringify(result.ast, null, 2);
			html += `<section class="result-section"><h3>ABSTRACT SYNTAX TREE</h3><pre>${escapeHtml(ast)}</pre></section>`;
		}
		return html;
	}

	function renderSuccess(result) {
		const tokens = result.tokens.map(tok =>
			`<span class="token"><b>${escapeHtml(tok.type)}</b> ${escapeHtml(tok.value)}</span>`
		).join("");

		const statements = result.ast.statements.length;

		const rows = Object.entries(result.symbols).map(([name, symbol]) => {
			const value = symbol.value === null ? "<uninitialized>" : symbol.value;
			return `<tr><td>${escapeHtml(name)}</td><td>${escapeHtml(symbol.type)}</td><td>${escapeHtml(value)}</td><td>${symbol.declared_line ?? "—"}</td></tr>`;
		}).join("");

		const ast = JSON.stringify(result.ast, null, 2);

		tabOutput.innerHTML = `
			<div class="summary">
				<span><b>${result.stats.token_count}</b>TOKENS</span>
				<span><b>${statements}</b>STATEMENTS</span>
				<span><b>${result.stats.symbol_count}</b>SYMBOLS</span>
			</div>
			<section class="result-section"><h3>TOKEN STREAM</h3><div class="token-list">${tokens || "<span class='token'>EMPTY</span>"}</div></section>
			<section class="result-section"><h3>SYMBOL TABLE</h3><table class="symbol-table"><thead><tr><th>NAME</th><th>TYPE</th><th>VALUE</th><th>LINE</th></tr></thead><tbody>${rows || "<tr><td colspan='4'>No declarations</td></tr>"}</tbody></table></section>
			<section class="result-section"><h3>ABSTRACT SYNTAX TREE</h3><pre>${escapeHtml(ast)}</pre></section>`;

		setStatus("COMPILED", "success");
	}

	function renderGrammar(grammar) {
		if (!grammar) return;

		// Production rules
		const rulesHTML = Object.entries(grammar.rules).map(([nt, prods]) => {
			const rhs = prods.map(p => `<code>${escapeHtml(p)}</code>`).join(" <span class='pipe'>|</span> ");
			return `<tr><td class="nt">${escapeHtml(nt)}</td><td>→</td><td>${rhs}</td></tr>`;
		}).join("");

		// FIRST sets
		const firstHTML = Object.entries(grammar.first).map(([sym, vals]) =>
			`<tr><td class="nt">FIRST(${escapeHtml(sym)})</td><td>=</td><td><span class="set-vals">${vals.map(v => `<code>${escapeHtml(v)}</code>`).join(" ")}</span></td></tr>`
		).join("");

		// FOLLOW sets
		const followHTML = Object.entries(grammar.follow).map(([sym, vals]) =>
			`<tr><td class="nt">FOLLOW(${escapeHtml(sym)})</td><td>=</td><td><span class="set-vals">${vals.map(v => `<code>${escapeHtml(v)}</code>`).join(" ")}</span></td></tr>`
		).join("");

		tabGrammar.innerHTML = `
			<section class="result-section">
				<h3>CONTEXT-FREE GRAMMAR (CFG)</h3>
				<table class="grammar-table"><tbody>${rulesHTML}</tbody></table>
			</section>
			<section class="result-section">
				<h3>FIRST SETS</h3>
				<table class="grammar-table"><tbody>${firstHTML}</tbody></table>
			</section>
			<section class="result-section">
				<h3>FOLLOW SETS</h3>
				<table class="grammar-table"><tbody>${followHTML}</tbody></table>
			</section>`;
	}

	// ── Main compile ─────────────────────────────────────────────────────────
	async function compile() {
		compileButton.disabled = true;
		compileButton.querySelector("span:nth-child(2)").textContent = "Compiling...";
		resultsPanel.setAttribute("aria-busy", "true");
		setStatus("RUNNING", "idle");
		resetStages();

		try {
			const response = await fetch("/compile", {
				method: "POST",
				headers: { "Content-Type": "application/json", Accept: "application/json" },
				body: JSON.stringify({ source: sourceEditor.value }),
			});
			const result = await response.json();

			// Update pipeline stage indicators
			updateStages(result.pipeline);

			// Always render grammar if available
			if (result.grammar) renderGrammar(result.grammar);

			if (!response.ok || !result.success) {
				renderFailure(result);
			} else {
				renderSuccess(result);
			}

			// Switch to output tab after compile
			activateTab(tabOutput, btnOutput);

		} catch (error) {
			renderFailure({ error: { phase: "network", message: "Could not reach the compiler. Check the server and try again." } });
		} finally {
			compileButton.disabled = false;
			compileButton.querySelector("span:nth-child(2)").textContent = "Compile source";
			resultsPanel.setAttribute("aria-busy", "false");
		}
	}

	// ── Event listeners ──────────────────────────────────────────────────────
	sourceEditor.addEventListener("input", updateLineCount);
	compileButton.addEventListener("click", compile);
	resetButton.addEventListener("click", () => {
		sourceEditor.value = initialSource;
		updateLineCount();
		sourceEditor.focus();
	});
	sourceEditor.addEventListener("keydown", (event) => {
		if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
			event.preventDefault();
			compile();
		}
		if (event.key === "Tab") {
			event.preventDefault();
			const start = sourceEditor.selectionStart;
			const end   = sourceEditor.selectionEnd;
			sourceEditor.setRangeText("    ", start, end, "end");
			updateLineCount();
		}
	});
	updateLineCount();
})();
