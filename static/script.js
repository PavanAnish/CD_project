(() => {
	const sourceEditor = document.querySelector("#source-code");
	const compileButton = document.querySelector("#compile-button");
	const resetButton = document.querySelector("#reset-button");
	const resultContent = document.querySelector("#result-content");
	const statusPill = document.querySelector("#status-pill");
	const resultsPanel = document.querySelector(".results-panel");
	const lineCount = document.querySelector("#line-count");
	const initialSource = sourceEditor.value;

	function updateLineCount() {
		const lines = sourceEditor.value.split("\n").length;
		lineCount.textContent = `${lines} ${lines === 1 ? "LINE" : "LINES"}`;
	}

	function escapeHtml(value) {
		return String(value).replace(/[&<>"']/g, (char) => ({
			"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
		})[char]);
	}

	function setStatus(label, state) {
		statusPill.textContent = label;
		statusPill.className = `status-pill ${state}`;
	}

	function renderFailure(error) {
		const phase = error?.phase || "request";
		const location = Number.isInteger(error?.line) ? `Line ${error.line}, column ${error.column}` : "Request error";
		resultContent.innerHTML = `<div class="diagnostic"><b>${escapeHtml(phase)} error</b>${escapeHtml(error?.message || "Compilation failed.")}<small>${escapeHtml(location)}</small></div>`;
		setStatus("ERROR", "error");
	}

	function renderSuccess(result) {
		const tokens = result.tokens.map((token) => `<span class="token"><b>${escapeHtml(token.type)}</b> ${escapeHtml(token.value)}</span>`).join("");
		const statements = result.ast.statements.length;
		const rows = Object.entries(result.symbols).map(([name, symbol]) => {
			const value = symbol.value === null ? "<uninitialized>" : symbol.value;
			return `<tr><td>${escapeHtml(name)}</td><td>${escapeHtml(symbol.type)}</td><td>${escapeHtml(value)}</td><td>${symbol.declared_line}</td></tr>`;
		}).join("");
		const ast = JSON.stringify(result.ast, null, 2);
		resultContent.innerHTML = `
			<div class="summary"><span><b>${result.stats.token_count}</b>TOKENS</span><span><b>${statements}</b>STATEMENTS</span><span><b>${result.stats.symbol_count}</b>SYMBOLS</span></div>
			<section class="result-section"><h3>TOKEN STREAM</h3><div class="token-list">${tokens || "<span class='token'>EMPTY</span>"}</div></section>
			<section class="result-section"><h3>SYMBOL TABLE</h3><table class="symbol-table"><thead><tr><th>NAME</th><th>TYPE</th><th>VALUE</th><th>LINE</th></tr></thead><tbody>${rows || "<tr><td colspan='4'>No declarations</td></tr>"}</tbody></table></section>
			<section class="result-section"><h3>ABSTRACT SYNTAX TREE</h3><pre>${escapeHtml(ast)}</pre></section>`;
		setStatus("COMPILED", "success");
	}

	async function compile() {
		compileButton.disabled = true;
		compileButton.querySelector("span:nth-child(2)").textContent = "Compiling...";
		resultsPanel.setAttribute("aria-busy", "true");
		setStatus("RUNNING", "idle");
		try {
			const response = await fetch("/compile", {
				method: "POST",
				headers: { "Content-Type": "application/json", Accept: "application/json" },
				body: JSON.stringify({ source: sourceEditor.value }),
			});
			const result = await response.json();
			if (!response.ok || !result.success) renderFailure(result.error);
			else renderSuccess(result);
		} catch (error) {
			renderFailure({ phase: "network", message: "Could not reach the compiler. Check the server and try again." });
		} finally {
			compileButton.disabled = false;
			compileButton.querySelector("span:nth-child(2)").textContent = "Compile source";
			resultsPanel.setAttribute("aria-busy", "false");
		}
	}

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
			const end = sourceEditor.selectionEnd;
			sourceEditor.setRangeText("    ", start, end, "end");
			updateLineCount();
		}
	});
	updateLineCount();
})();
