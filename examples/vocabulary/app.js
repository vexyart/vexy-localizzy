// this_file: examples/vocabulary/app.js
// Translation & Review Tool Logic
document.addEventListener("DOMContentLoaded", () => {
  let currentLanguage = "en";
  let activeReviewKey = "vocab.node"; // Default active review key
  
  // Local mutable copy of translations
  const translations = JSON.parse(JSON.stringify(vocabularyTranslations));

  // --- 1. Basic ICU Plural and Index Formatting Engine ---
  
  // Format string with index-based placeholders (e.g. {0}, {1})
  function formatIndexString(template, args) {
    if (!args || args.length === 0) return template;
    return template.replace(/\{(\d+)\}/g, (match, index) => {
      const val = args[index];
      return typeof val !== 'undefined' ? val : match;
    });
  }

  // Basic ICU Plural Parser: parses simple {count, plural, =0 {no glyphs} one {one glyph} other {{count} glyphs}}
  function formatPluralString(template, count, total) {
    const pluralRegex = /\{count,\s*plural,\s*(=0|one|other)\s*\{([^}]+)\}\s*(=0|one|other)\s*\{([^}]+)\}\s*(=0|one|other)\s*\{([^}]+)\}\}/g;
    
    let result = template.replace(pluralRegex, (match) => {
      // Parse branches
      // A robust parsing splits by closing and opening blocks
      // For safety in this sandbox, we parse manually:
      const body = match.slice(15, -2); // Remove "{count, plural, " and "}}"
      
      const branches = {};
      const parts = body.split('}');
      parts.forEach(part => {
        const trimPart = part.trim();
        if (!trimPart) return;
        const indexOpen = trimPart.indexOf('{');
        if (indexOpen === -1) return;
        const key = trimPart.slice(0, indexOpen).trim();
        const value = trimPart.slice(indexOpen + 1);
        branches[key] = value;
      });

      let selected = branches['other'] || '';
      if (count === 0 && branches['=0']) {
        selected = branches['=0'];
      } else if (count === 1 && branches['one']) {
        selected = branches['one'];
      }

      // Replace count placeholder within selection
      return selected.replace(/\{count\}/g, count);
    });

    // Replace {total} placeholder
    result = result.replace(/\{total\}/g, total);
    return result;
  }

  // Dynamic Translate Helper
  function translate(key, args = null, count = null, total = null) {
    const entry = translations[key];
    if (!entry) return key;

    // Default to English if the target language is missing or untranslated
    let template = entry[currentLanguage] || entry["en"] || key;
    if (typeof template !== 'string') {
      // Fallback for metadata keys like languages.en
      template = entry.translation || key;
    }

    if (count !== null && total !== null) {
      return formatPluralString(template, count, total);
    }
    if (args) {
      return formatIndexString(template, args);
    }
    return template;
  }

  // --- 2. Update UI Translations ---
  function updateUiTranslations() {
    // 1. Update document/editor title
    document.title = translate("editor.title");

    // 2. Translate standard elements with [data-i18n]
    document.querySelectorAll("[data-i18n]").forEach(el => {
      const key = el.getAttribute("data-i18n");
      const hasAmpersand = el.classList.contains("menu-title") || el.classList.contains("dropdown-item") || el.tagName === "BUTTON";
      
      // Check if it's a message with plural values embedded
      if (key === "msg.selectedGlyphsCount") {
        const vals = JSON.parse(el.getAttribute("data-vals") || '{"count":0,"total":0}');
        el.innerText = translate(key, null, vals.count, vals.total);
        return;
      }

      let translatedText = translate(key);

      // Handle ampersand mnemonics in UI elements (e.g. &File -> <u>F</u>ile)
      if (hasAmpersand && translatedText.includes("&")) {
        const index = translatedText.indexOf("&");
        const char = translatedText[index + 1];
        translatedText = translatedText.slice(0, index) + `<u>${char}</u>` + translatedText.slice(index + 2);
        el.innerHTML = translatedText;
      } else {
        el.innerText = translatedText;
      }
    });

    // 3. Update active tooltips
    document.querySelectorAll("[data-tooltip]").forEach(el => {
      const tooltipKey = el.getAttribute("data-tooltip");
      el.setAttribute("data-tooltip", translate(tooltipKey));
    });

    // 4. Update status bar active indicator
    const statusMsg = document.getElementById("status-message");
    statusMsg.innerText = translate("editor.statusBar.ready");

    // 5. Update right label language signpost
    document.getElementById("active-lang-label").innerText = currentLanguage.toUpperCase();

    // 6. Reload vocabulary glossary list
    populateVocabularyList();
    
    // 7. Reload active review panel
    loadActiveReviewKey(activeReviewKey);
  }

  // --- 3. Glossary & Disambiguation List Handling ---
  function populateVocabularyList() {
    const listContainer = document.getElementById("vocab-list");
    listContainer.innerHTML = "";

    // Group keys from vocabularyTranslations that are "vocab.*"
    const vocabKeys = Object.keys(translations).filter(k => k.startsWith("vocab."));

    vocabKeys.forEach(key => {
      const li = document.createElement("li");
      li.className = "vocab-item";
      if (key === activeReviewKey) li.classList.add("active");
      
      const termName = translate(key);
      const context = translations[key].context || "";
      li.innerHTML = `<strong>${termName}</strong> <span style="font-size: 10px; color: var(--text-muted); display:block; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">${context}</span>`;
      
      li.addEventListener("click", () => {
        document.querySelectorAll(".vocab-item").forEach(item => item.classList.remove("active"));
        li.classList.add("active");
        loadActiveReviewKey(key);
      });
      listContainer.appendChild(li);
    });
  }

  // --- 4. Load & Save Translation in Review Panel ---
  function loadActiveReviewKey(key) {
    activeReviewKey = key;
    const entry = translations[key];
    if (!entry) return;

    document.getElementById("review-key").innerText = key;
    document.getElementById("review-context").innerText = entry.context || "No context specified.";
    document.getElementById("review-source").innerText = entry.en || "";
    
    const inputField = document.getElementById("review-input");
    // Show current language translation if exists, otherwise show empty/default
    inputField.value = entry[currentLanguage] || "";
  }

  // Save reviewed translation button click handler
  document.getElementById("btn-save-translation").addEventListener("click", () => {
    const inputVal = document.getElementById("review-input").value.trim();
    if (!activeReviewKey || !translations[activeReviewKey]) return;

    // Update value in local dictionary memory
    translations[activeReviewKey][currentLanguage] = inputVal;

    // Trigger visual UI update instantly
    updateUiTranslations();

    // Toast/Status Update
    const statusMsg = document.getElementById("status-message");
    statusMsg.innerText = `Saved translation for key: ${activeReviewKey}`;
    setTimeout(() => {
      statusMsg.innerText = translate("editor.statusBar.ready");
    }, 2000);
  });

  // --- 5. Export Translations as JSON file ---
  document.getElementById("btn-export-json").addEventListener("click", () => {
    // Generate JSON representation
    const jsonString = JSON.stringify(translations, null, 2);
    const blob = new Blob([jsonString], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement("a");
    a.href = url;
    a.download = `typography_vocab_${currentLanguage}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  });

  // --- 6. Interactivity & Workspace Events ---
  
  // Language Switcher change
  document.getElementById("lang-select").addEventListener("change", (e) => {
    currentLanguage = e.target.value;
    updateUiTranslations();
  });

  // Workspace Node Vector interactive highlights
  document.querySelectorAll(".vector-node, .bezier-handle").forEach(node => {
    node.addEventListener("mouseenter", (e) => {
      let xVal = "500";
      let yVal = "300";
      if (node.tagName === "circle") {
        xVal = node.getAttribute("cx");
        yVal = node.getAttribute("cy");
      } else if (node.tagName === "rect") {
        xVal = (parseInt(node.getAttribute("x")) + 4).toString();
        yVal = (parseInt(node.getAttribute("y")) + 4).toString();
      }
      document.getElementById("val-x").innerText = xVal;
      document.getElementById("val-y").innerText = yVal;
    });
  });

  // Hotspot Overlay clicks (connects workspace directly to the review editor)
  document.querySelectorAll(".hover-hotspot, .metric-block").forEach(hotspot => {
    hotspot.addEventListener("click", () => {
      const key = hotspot.getAttribute("data-key");
      if (key) {
        loadActiveReviewKey(key);
        // Focus review input
        document.getElementById("review-input").focus();
        // Highlight in vocabulary list
        populateVocabularyList();
      }
    });
  });

  // Initialize UI on startup
  updateUiTranslations();
});
