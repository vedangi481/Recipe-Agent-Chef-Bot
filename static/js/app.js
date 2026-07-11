/**
 * ChefBot — AI Recipe Preparation Agent
 * Frontend JavaScript: Chat, Ingredients, Dietary Filters, Panels, Dark Mode
 */

"use strict";

// ================================================================
// State
// ================================================================
const State = {
  ingredients:    [],       // Current ingredient list
  chatHistory:    [],       // [{role:"user"|"assistant", content:"..."}]
  currentRecipe:  null,     // Last AI-generated recipe content
  favorites:      [],       // Saved favorites (fetched from server)
  dietaryFilters: [],       // Active dietary checkboxes
  darkMode:       false,    // Current theme
};

// ================================================================
// DOM references
// ================================================================
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

const DOM = {
  chatMessages:     $("#chatMessages"),
  chatInput:        $("#chatInput"),
  sendBtn:          $("#sendBtn"),
  clearChatBtn:     $("#clearChatBtn"),
  typingIndicator:  $("#typingIndicator"),
  ingredientInput:  $("#ingredientInput"),
  addIngBtn:        $("#addIngredientBtn"),
  ingredientChips:  $("#ingredientChips"),
  clearIngBtn:      $("#clearIngredientsBtn"),
  findRecipesBtn:   $("#findRecipesBtn"),
  recipeGrid:       $("#recipeGrid"),
  guideEmptyState:  $("#guideEmptyState"),
  guideContent:     $("#guideContent"),
  guideBody:        $("#guideBody"),
  darkModeToggle:   $("#darkModeToggle"),
  darkModeIcon:     $("#darkModeIcon"),
  favCount:         $("#favCount"),
  historyList:      $("#historyList"),
  favoritesList:    $("#favoritesList"),
  clearHistoryBtn:  $("#clearHistoryBtn"),
  // Nutrition panel
  calorieDisplay:   $("#calorieDisplay"),
  proteinVal:       $("#proteinVal"),
  carbsVal:         $("#carbsVal"),
  fatVal:           $("#fatVal"),
  fiberVal:         $("#fiberVal"),
  proteinBar:       $("#proteinBar"),
  carbsBar:         $("#carbsBar"),
  fatBar:           $("#fatBar"),
  fiberBar:         $("#fiberBar"),
  analyzeNutritionBtn: $("#analyzeNutritionBtn"),
  // Substitution modal
  substitutionInput:     $("#substitutionInput"),
  findSubstitutionBtn:   $("#findSubstitutionBtn"),
  substitutionResult:    $("#substitutionResult"),
  // Nutrition modal
  nutritionInput:        $("#nutritionInput"),
  analyzeNutritionModalBtn: $("#analyzeNutritionModalBtn"),
  nutritionModalResult:  $("#nutritionModalResult"),
};

// ================================================================
// Initialisation
// ================================================================
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initChatInput();
  initIngredientPanel();
  initDietaryFilters();
  initQuickPills();
  initTabSwitching();
  initQuickToolButtons();
  initModals();
  initHistoryPanel();
  initFavoritesPanel();
  loadFavorites();
  scrollChatToBottom();
});

// ================================================================
// Theme (dark / light)
// ================================================================
function initTheme() {
  const stored = localStorage.getItem("chefbot-theme") || "light";
  applyTheme(stored);

  DOM.darkModeToggle.addEventListener("click", () => {
    applyTheme(State.darkMode ? "light" : "dark");
  });
}

function applyTheme(theme) {
  State.darkMode = theme === "dark";
  document.documentElement.setAttribute("data-bs-theme", theme);
  DOM.darkModeIcon.className = State.darkMode ? "bi bi-sun-fill" : "bi bi-moon-stars-fill";
  localStorage.setItem("chefbot-theme", theme);
}

// ================================================================
// Chat input handling
// ================================================================
function initChatInput() {
  // Pass no arguments so the browser PointerEvent is not forwarded to sendMessage
  DOM.sendBtn.addEventListener("click", () => sendMessage());

  DOM.chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  DOM.clearChatBtn.addEventListener("click", () => {
    if (!confirm("Clear all chat history?")) return;
    State.chatHistory = [];
    DOM.chatMessages.innerHTML = "";
    fetch("/api/history", { method: "DELETE" });
    showToast("Chat cleared.", "info");
  });
}

// ================================================================
// Send message to AI
// ================================================================
async function sendMessage(overrideMessage = null) {
  // Guard: ignore any non-string argument (e.g. a stray PointerEvent)
  const override = typeof overrideMessage === "string" ? overrideMessage : null;
  const rawMessage = override || DOM.chatInput.value.trim();
  if (!rawMessage) return;

  // Clear input
  if (!override) DOM.chatInput.value = "";

  // Add user bubble
  appendMessage("user", rawMessage);
  State.chatHistory.push({ role: "user", content: rawMessage });

  // Show typing indicator
  setTyping(true);
  DOM.sendBtn.disabled = true;

  try {
    const body = {
      message:          rawMessage,
      ingredients:      State.ingredients,
      dietary_filters:  State.dietaryFilters,
      history:          State.chatHistory.slice(-8),
    };

    const res  = await fetch("/api/chat", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
    });

    const data = await res.json();

    if (data.error) throw new Error(data.error);

    const reply = data.response || "Sorry, I couldn't generate a response.";

    // Add AI bubble
    appendMessage("assistant", reply, { showActions: true });
    State.chatHistory.push({ role: "assistant", content: reply });
    State.currentRecipe = reply;

    // Try to parse and display nutrition from the response
    parseAndDisplayNutrition(reply);

  } catch (err) {
    appendMessage("assistant", `⚠️ Error: ${err.message}. Please try again.`);
  } finally {
    setTyping(false);
    DOM.sendBtn.disabled = false;
    scrollChatToBottom();
  }
}

// ================================================================
// Append a chat message bubble
// ================================================================
function appendMessage(role, content, options = {}) {
  const wrapper = document.createElement("div");
  wrapper.className = `message-wrapper ${role === "user" ? "user-message" : "assistant-message"}`;

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";

  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.textContent = role === "user" ? "👤" : "👨‍🍳";

  const contentDiv = document.createElement("div");
  contentDiv.className = "message-content";

  // Render markdown (marked.js)
  try {
    contentDiv.innerHTML = marked.parse(content);
  } catch {
    contentDiv.textContent = content;
  }

  // Timestamp
  const ts = document.createElement("div");
  ts.className = "msg-timestamp";
  ts.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  contentDiv.appendChild(ts);

  // Action buttons for assistant messages
  if (role === "assistant" && options.showActions) {
    const actions = document.createElement("div");
    actions.className = "message-actions";

    const saveBtn = createActionBtn("bi-bookmark-plus", "Save Recipe", () => saveToFavorites(content));
    const guideBtn = createActionBtn("bi-journal-text", "View Guide", () => showCookingGuide(content));
    const copyBtn  = createActionBtn("bi-clipboard", "Copy", () => copyToClipboard(content, copyBtn));

    actions.appendChild(saveBtn);
    actions.appendChild(guideBtn);
    actions.appendChild(copyBtn);
    contentDiv.appendChild(actions);
  }

  bubble.appendChild(avatar);
  bubble.appendChild(contentDiv);
  wrapper.appendChild(bubble);
  DOM.chatMessages.appendChild(wrapper);
  scrollChatToBottom();
}

function createActionBtn(iconClass, label, onClick) {
  const btn = document.createElement("button");
  btn.className = "msg-action-btn";
  btn.innerHTML = `<i class="bi ${iconClass} me-1"></i>${label}`;
  btn.addEventListener("click", onClick);
  return btn;
}

// ================================================================
// Typing indicator
// ================================================================
function setTyping(show) {
  DOM.typingIndicator.classList.toggle("d-none", !show);
  if (show) scrollChatToBottom();
}

function scrollChatToBottom() {
  requestAnimationFrame(() => {
    DOM.chatMessages.scrollTop = DOM.chatMessages.scrollHeight;
  });
}

// ================================================================
// Ingredient Panel
// ================================================================
function initIngredientPanel() {
  DOM.addIngBtn.addEventListener("click", addIngredient);
  DOM.ingredientInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); addIngredient(); }
  });
  DOM.clearIngBtn.addEventListener("click", () => {
    State.ingredients = [];
    renderIngredientChips();
  });
  DOM.findRecipesBtn.addEventListener("click", findRecipes);

  // Quick-add buttons
  $$(".quick-add-btn").forEach(btn => {
    btn.addEventListener("click", () => addIngredientByName(btn.dataset.ing));
  });
}

function addIngredient() {
  const val = DOM.ingredientInput.value.trim();
  if (!val) return;
  addIngredientByName(val);
  DOM.ingredientInput.value = "";
}

function addIngredientByName(name) {
  const normalized = name.trim();
  if (!normalized) return;
  if (State.ingredients.some(i => i.toLowerCase() === normalized.toLowerCase())) {
    showToast(`"${normalized}" is already in your list.`, "warning");
    return;
  }
  State.ingredients.push(normalized);
  renderIngredientChips();
}

function renderIngredientChips() {
  if (State.ingredients.length === 0) {
    DOM.ingredientChips.innerHTML = '<span class="text-muted small">No ingredients added yet.</span>';
    return;
  }
  DOM.ingredientChips.innerHTML = "";
  State.ingredients.forEach((ing, idx) => {
    const chip = document.createElement("span");
    chip.className = "ingredient-chip";
    chip.innerHTML = `${ing}<button class="remove-chip" title="Remove">✕</button>`;
    chip.querySelector(".remove-chip").addEventListener("click", () => {
      State.ingredients.splice(idx, 1);
      renderIngredientChips();
    });
    DOM.ingredientChips.appendChild(chip);
  });
}

// ================================================================
// Find Recipes (ingredient-based)
// ================================================================
async function findRecipes() {
  if (State.ingredients.length === 0) {
    showToast("Please add at least one ingredient first.", "warning");
    return;
  }

  setButtonLoading(DOM.findRecipesBtn, true);

  // Switch to recipes tab
  switchTab("recipes");

  // Generate a chat message too
  const message = `I have these ingredients: ${State.ingredients.join(", ")}. What recipes can I make?${State.dietaryFilters.length ? " Dietary preferences: " + State.dietaryFilters.join(", ") : ""}`;
  await sendMessage(message);

  // Also show recipe cards from static dataset
  displayRecipeCards();
  setButtonLoading(DOM.findRecipesBtn, false);
}

function displayRecipeCards() {
  // Filter from embedded recipe data
  const cards = getSuggestedRecipes();
  DOM.recipeGrid.innerHTML = "";

  if (cards.length === 0) {
    DOM.recipeGrid.innerHTML = `
      <div class="col-12 text-center py-5 text-muted">
        <i class="bi bi-search display-4 mb-3 d-block"></i>
        <p>No matching recipes found for your ingredients. Try adding more items!</p>
      </div>`;
    return;
  }

  cards.forEach(recipe => {
    const tmpl  = document.getElementById("recipeCardTemplate");
    const clone = tmpl.content.cloneNode(true);
    const card  = clone.querySelector(".col-12");

    card.querySelector(".recipe-card-title").textContent = recipe.name;
    card.querySelector(".time-val").textContent = recipe.total_time + " min";
    card.querySelector(".servings-val").textContent = recipe.servings + " servings";
    card.querySelector(".calorie-val").textContent = recipe.nutrition_per_serving.calories + " kcal";

    // Difficulty badge
    const badge = card.querySelector(".difficulty-badge");
    badge.textContent = recipe.difficulty;
    badge.classList.add(recipe.difficulty.toLowerCase());

    // Dietary tags
    const tagsContainer = card.querySelector(".dietary-tags");
    (recipe.dietary || []).slice(0, 3).forEach(tag => {
      const span = document.createElement("span");
      span.className = "dietary-tag";
      span.textContent = tag;
      tagsContainer.appendChild(span);
    });

    // Ingredient match percentage
    const matchPct = calculateMatch(recipe.main_ingredients);
    card.querySelector(".match-pct").textContent = matchPct + "%";
    card.querySelector(".match-bar").style.width = matchPct + "%";

    // Cook now button
    card.querySelector(".cook-now-btn").addEventListener("click", () => {
      const query = `Give me a detailed step-by-step recipe for ${recipe.name} using: ${State.ingredients.join(", ")}`;
      switchTab("chat");
      sendMessage(query);
    });

    DOM.recipeGrid.appendChild(clone);
  });
}

function calculateMatch(recipeIngredients) {
  if (!recipeIngredients || recipeIngredients.length === 0) return 0;
  const userIngs = State.ingredients.map(i => i.toLowerCase());
  let matches = 0;
  recipeIngredients.forEach(ri => {
    if (userIngs.some(ui => ui.includes(ri.toLowerCase()) || ri.toLowerCase().includes(ui))) {
      matches++;
    }
  });
  return Math.round((matches / recipeIngredients.length) * 100);
}

function getSuggestedRecipes() {
  // Client-side recipe cards built from the recipes_dataset
  const recipes = getEmbeddedRecipes();

  let filtered = recipes;

  // Apply dietary filters
  if (State.dietaryFilters.length > 0) {
    filtered = filtered.filter(r =>
      State.dietaryFilters.some(df => r.dietary && r.dietary.includes(df))
    );
  }

  // Score by ingredient match
  const scored = filtered.map(r => ({
    ...r,
    matchScore: calculateMatch(r.main_ingredients),
  }));

  // Sort by match score descending
  scored.sort((a, b) => b.matchScore - a.matchScore);

  return scored.slice(0, 6);
}

// Embedded recipe cards dataset (mirrors data/recipes_dataset.json)
function getEmbeddedRecipes() {
  return [
    { id:"R001", name:"Aloo Matar",            difficulty:"Easy",   total_time:40, servings:4, dietary:["Vegetarian","Gluten-Free","Vegan"],    main_ingredients:["potato","peas","onion","tomato"], nutrition_per_serving:{calories:180} },
    { id:"R002", name:"Paneer Butter Masala",   difficulty:"Medium", total_time:50, servings:4, dietary:["Vegetarian","Gluten-Free"],             main_ingredients:["paneer","tomato","onion","cream","butter"], nutrition_per_serving:{calories:380} },
    { id:"R003", name:"Palak Paneer",           difficulty:"Medium", total_time:40, servings:4, dietary:["Vegetarian","Gluten-Free","High-Protein"], main_ingredients:["paneer","spinach","onion","tomato"], nutrition_per_serving:{calories:280} },
    { id:"R004", name:"Masoor Dal",             difficulty:"Easy",   total_time:25, servings:4, dietary:["Vegan","Vegetarian","Gluten-Free","High-Protein","Diabetic-Friendly"], main_ingredients:["red lentils","onion","tomato","cumin"], nutrition_per_serving:{calories:220} },
    { id:"R005", name:"Vegetable Biryani",      difficulty:"Hard",   total_time:75, servings:6, dietary:["Vegetarian"],                           main_ingredients:["basmati rice","mixed vegetables","yogurt","saffron"], nutrition_per_serving:{calories:420} },
    { id:"R006", name:"Egg Bhurji",             difficulty:"Easy",   total_time:15, servings:2, dietary:["Vegetarian","Gluten-Free","High-Protein"], main_ingredients:["eggs","onion","tomato","green chili","butter"], nutrition_per_serving:{calories:260} },
    { id:"R007", name:"Vegetable Fried Rice",   difficulty:"Easy",   total_time:25, servings:4, dietary:["Vegan","Vegetarian"],                   main_ingredients:["cooked rice","mixed vegetables","soy sauce","garlic"], nutrition_per_serving:{calories:320} },
    { id:"R008", name:"Khichdi",                difficulty:"Easy",   total_time:30, servings:4, dietary:["Vegetarian","Gluten-Free","Diabetic-Friendly"], main_ingredients:["rice","moong dal","onion","tomato","ghee"], nutrition_per_serving:{calories:280} },
    { id:"R009", name:"Chana Masala",           difficulty:"Easy",   total_time:35, servings:4, dietary:["Vegan","Vegetarian","Gluten-Free","High-Protein"], main_ingredients:["chickpeas","onion","tomato","ginger-garlic paste"], nutrition_per_serving:{calories:250} },
    { id:"R010", name:"Banana Oat Pancakes",    difficulty:"Easy",   total_time:20, servings:2, dietary:["Vegetarian","Gluten-Free"],              main_ingredients:["banana","oats","eggs"], nutrition_per_serving:{calories:290} },
    { id:"R011", name:"Tomato Rice",            difficulty:"Easy",   total_time:30, servings:4, dietary:["Vegan","Vegetarian","Gluten-Free"],      main_ingredients:["cooked rice","tomato","onion","mustard seeds","curry leaves"], nutrition_per_serving:{calories:240} },
    { id:"R012", name:"Aloo Paratha",           difficulty:"Medium", total_time:50, servings:4, dietary:["Vegetarian"],                            main_ingredients:["potato","whole wheat flour","butter","spices"], nutrition_per_serving:{calories:360} },
  ];
}

// ================================================================
// Dietary Filters
// ================================================================
function initDietaryFilters() {
  $$(".dietary-filter").forEach(cb => {
    cb.addEventListener("change", () => {
      State.dietaryFilters = $$(".dietary-filter:checked").map(c => c.value);
    });
  });
}

// ================================================================
// Example pills
// ================================================================
function initQuickPills() {
  $$(".pill-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const query = btn.dataset.query;
      DOM.chatInput.value = query;
      switchTab("chat");
      sendMessage();
    });
  });
}

// ================================================================
// Tab switching
// ================================================================
function initTabSwitching() {
  $$(".nav-link", document.getElementById("mainTabs")).forEach(btn => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
}

function switchTab(tabName) {
  // Deactivate all tabs
  $$(".nav-link", document.getElementById("mainTabs")).forEach(b => {
    b.classList.toggle("active", b.dataset.tab === tabName);
  });

  // Show/hide panels
  const panels = { chat: "tabChat", recipes: "tabRecipes", guide: "tabGuide" };
  Object.entries(panels).forEach(([name, id]) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (name === tabName) {
      el.classList.remove("d-none");
      el.classList.add("active");
    } else {
      el.classList.add("d-none");
      el.classList.remove("active");
    }
  });
}

// ================================================================
// Cooking Guide Tab
// ================================================================
function showCookingGuide(content) {
  DOM.guideEmptyState.classList.add("d-none");
  DOM.guideContent.classList.remove("d-none");
  try {
    DOM.guideBody.innerHTML = marked.parse(content);
  } catch {
    DOM.guideBody.textContent = content;
  }
  switchTab("guide");
  showToast("Cooking guide ready!", "success");
}

// ================================================================
// Quick Tools
// ================================================================
function initQuickToolButtons() {
  // Substitution tool
  $("#substitutionToolBtn").addEventListener("click", () => {
    const modal = new bootstrap.Modal("#substitutionModal");
    modal.show();
  });

  // Nutrition tool
  $("#nutritionToolBtn").addEventListener("click", () => {
    const modal = new bootstrap.Modal("#nutritionModal");
    modal.show();
  });

  // Leftover ideas
  $("#leftoverToolBtn").addEventListener("click", () => {
    const msg = State.ingredients.length > 0
      ? `I have leftover: ${State.ingredients.join(", ")}. Suggest recipes to use them up and minimize waste.`
      : "Suggest creative recipes for common leftover ingredients like rice, dal, rotis, and vegetables.";
    switchTab("chat");
    DOM.chatInput.value = msg;
    sendMessage();
  });

  // Cooking tips
  $("#cookingTipsBtn").addEventListener("click", () => {
    switchTab("chat");
    DOM.chatInput.value = "Give me 5 essential cooking tips and tricks for beginner Indian home cooks.";
    sendMessage();
  });

  // Analyze current recipe nutrition
  DOM.analyzeNutritionBtn.addEventListener("click", () => {
    if (!State.currentRecipe) {
      showToast("Generate a recipe first by chatting with ChefBot!", "warning");
      return;
    }
    const modal = new bootstrap.Modal("#nutritionModal");
    DOM.nutritionInput.value = "Analyze nutrition for: " + State.currentRecipe.substring(0, 200);
    modal.show();
  });
}

// ================================================================
// Modals
// ================================================================
function initModals() {
  // Substitution modal
  DOM.findSubstitutionBtn.addEventListener("click", findSubstitution);
  DOM.substitutionInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") findSubstitution();
  });

  // Nutrition modal
  DOM.analyzeNutritionModalBtn.addEventListener("click", analyzeNutrition);
  DOM.nutritionInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") analyzeNutrition();
  });
}

async function findSubstitution() {
  const ingredient = DOM.substitutionInput.value.trim();
  if (!ingredient) return;

  setButtonLoading(DOM.findSubstitutionBtn, true);
  DOM.substitutionResult.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm text-info" role="status"></div> Finding substitutions…</div>';
  DOM.substitutionResult.classList.remove("d-none");

  try {
    const res  = await fetch("/api/substitution", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ ingredient }),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    DOM.substitutionResult.innerHTML = marked.parse(data.response || "No substitutions found.");
  } catch (err) {
    DOM.substitutionResult.innerHTML = `<p class="text-danger">Error: ${err.message}</p>`;
  } finally {
    setButtonLoading(DOM.findSubstitutionBtn, false);
  }
}

async function analyzeNutrition() {
  const query = DOM.nutritionInput.value.trim();
  if (!query) return;

  setButtonLoading(DOM.analyzeNutritionModalBtn, true);
  DOM.nutritionModalResult.innerHTML = '<div class="text-center py-3"><div class="spinner-border spinner-border-sm text-danger" role="status"></div> Analyzing nutrition…</div>';
  DOM.nutritionModalResult.classList.remove("d-none");

  try {
    const res  = await fetch("/api/nutrition", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ query }),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    const responseText = data.response || "No information found.";
    DOM.nutritionModalResult.innerHTML = marked.parse(responseText);

    // ✅ Also update the right-side Nutrition Panel with parsed values
    parseAndDisplayNutrition(responseText);

  } catch (err) {
    DOM.nutritionModalResult.innerHTML = `<p class="text-danger">Error: ${err.message}</p>`;
  } finally {
    setButtonLoading(DOM.analyzeNutritionModalBtn, false);
  }
}

// ================================================================
// Nutrition display panel (sidebar)
// ================================================================
function parseAndDisplayNutrition(responseText) {
  // ---- Helper: try multiple regex patterns and return first match ----
  function extract(patterns) {
    for (const re of patterns) {
      const m = responseText.match(re);
      if (m) return parseFloat(m[1]);
    }
    return null;
  }

  // Calories — handles: "280 kcal", "Calories: 280", "~280 cal", "280 calories per serving"
  const calories = extract([
    /(\d{2,4})\s*(?:k?cal(?:ories)?)\b/i,
    /calories?[:\s]+~?(\d{2,4})/i,
    /energy[:\s]+~?(\d{2,4})/i,
  ]);

  // Protein — handles: "15g protein", "Protein: 15g", "protein 15 g", "15 grams protein"
  const protein = extract([
    /(\d+\.?\d*)\s*g(?:rams?)?\s*(?:of\s*)?protein/i,
    /protein[:\s]+~?(\d+\.?\d*)\s*g/i,
    /protein[:\s]+~?(\d+\.?\d*)/i,
  ]);

  // Carbs — handles: "45g carbs", "Carbohydrates: 45g", "carbs 45 g"
  const carbs = extract([
    /(\d+\.?\d*)\s*g(?:rams?)?\s*(?:of\s*)?carb(?:ohydrate)?s?/i,
    /carb(?:ohydrate)?s?[:\s]+~?(\d+\.?\d*)\s*g/i,
    /carb(?:ohydrate)?s?[:\s]+~?(\d+\.?\d*)/i,
  ]);

  // Fat — handles: "10g fat", "Fat: 10g", "total fat 10g"
  const fat = extract([
    /(\d+\.?\d*)\s*g(?:rams?)?\s*(?:of\s*)?(?:total\s*)?fat/i,
    /(?:total\s*)?fat[:\s]+~?(\d+\.?\d*)\s*g/i,
    /(?:total\s*)?fat[:\s]+~?(\d+\.?\d*)/i,
  ]);

  // Fiber — handles: "5g fiber", "Fiber: 5g", "dietary fiber 5g"
  const fiber = extract([
    /(\d+\.?\d*)\s*g(?:rams?)?\s*(?:dietary\s*)?fiber/i,
    /(?:dietary\s*)?fiber[:\s]+~?(\d+\.?\d*)\s*g/i,
    /(?:dietary\s*)?fiber[:\s]+~?(\d+\.?\d*)/i,
  ]);

  // Check if we found any useful data
  const hasData = calories !== null || protein !== null || carbs !== null || fat !== null;

  if (hasData) {
    // Use extracted values; fall back to "—" where missing
    const cal = calories || 0;
    const pro = protein  || 0;
    const crb = carbs    || 0;
    const ftt = fat      || 0;
    const fib = fiber    || 0;
    const total = pro + crb + ftt || 1; // avoid div/0

    DOM.calorieDisplay.textContent = cal > 0 ? cal : "—";
    DOM.proteinVal.textContent     = pro > 0 ? pro + "g" : "—";
    DOM.carbsVal.textContent       = crb > 0 ? crb + "g" : "—";
    DOM.fatVal.textContent         = ftt > 0 ? ftt + "g" : "—";
    DOM.fiberVal.textContent       = fib > 0 ? fib + "g" : "—";

    // Animate progress bars
    DOM.proteinBar.style.width = Math.min(100, Math.round(pro / total * 100)) + "%";
    DOM.carbsBar.style.width   = Math.min(100, Math.round(crb / total * 100)) + "%";
    DOM.fatBar.style.width     = Math.min(100, Math.round(ftt / total * 100)) + "%";
    DOM.fiberBar.style.width   = Math.min(100, Math.round(fib / total * 100)) + "%";

  } else {
    // Fallback: if response looks like a recipe but no numbers found,
    // show estimated placeholder values so the panel isn't blank
    const isRecipe = /\b(recipe|ingredient|cook|serve|serving|tablespoon|teaspoon|cup|gram|kg|ml|litre|heat|stir|boil|fry|bake|simmer|mix|chop|slice|dice)\b/i.test(responseText);
    if (isRecipe) {
      // Sensible generic estimates for an average Indian dish
      DOM.calorieDisplay.textContent = "~280";
      DOM.proteinVal.textContent     = "~10g";
      DOM.carbsVal.textContent       = "~38g";
      DOM.fatVal.textContent         = "~9g";
      DOM.fiberVal.textContent       = "~4g";
      DOM.proteinBar.style.width     = "18%";
      DOM.carbsBar.style.width       = "65%";
      DOM.fatBar.style.width         = "15%";
      DOM.fiberBar.style.width       = "7%";
    }
  }
}

// ================================================================
// History Panel
// ================================================================
function initHistoryPanel() {
  DOM.clearHistoryBtn.addEventListener("click", async () => {
    if (!confirm("Clear all session history?")) return;
    await fetch("/api/history", { method: "DELETE" });
    DOM.historyList.innerHTML = '<p class="text-muted text-center py-4">History cleared.</p>';
    State.chatHistory = [];
    showToast("History cleared.", "info");
  });

  // Load history when offcanvas opens
  document.getElementById("historyPanel").addEventListener("show.bs.offcanvas", loadHistory);
}

async function loadHistory() {
  try {
    const res  = await fetch("/api/history");
    const data = await res.json();
    const items = data.history || [];

    if (items.length === 0) {
      DOM.historyList.innerHTML = '<p class="text-muted text-center py-4">No history yet. Start chatting with ChefBot!</p>';
      return;
    }

    DOM.historyList.innerHTML = "";
    items.slice().reverse().forEach(item => {
      const div = document.createElement("div");
      div.className = "history-item";
      div.innerHTML = `
        <div class="history-query">${escapeHtml(item.user)}</div>
        <div class="history-timestamp">${new Date(item.timestamp).toLocaleString()}</div>`;
      div.addEventListener("click", () => {
        // Re-display this exchange in chat
        appendMessage("user",      item.user);
        appendMessage("assistant", item.assistant, { showActions: true });
        bootstrap.Offcanvas.getInstance("#historyPanel")?.hide();
        switchTab("chat");
      });
      DOM.historyList.appendChild(div);
    });
  } catch (err) {
    DOM.historyList.innerHTML = `<p class="text-danger p-3">Failed to load history: ${err.message}</p>`;
  }
}

// ================================================================
// Favorites Panel
// ================================================================
function initFavoritesPanel() {
  document.getElementById("favoritesPanel").addEventListener("show.bs.offcanvas", loadFavorites);
}

async function loadFavorites() {
  try {
    const res  = await fetch("/api/favorites");
    const data = await res.json();
    State.favorites = data.favorites || [];
    renderFavorites();
    updateFavCount();
  } catch { /* ignore on initial load */ }
}

function renderFavorites() {
  if (State.favorites.length === 0) {
    DOM.favoritesList.innerHTML = '<p class="text-muted text-center py-4">No saved recipes yet. Use the <strong>Save Recipe</strong> button in any AI response!</p>';
    return;
  }

  DOM.favoritesList.innerHTML = "";
  State.favorites.slice().reverse().forEach(fav => {
    const div = document.createElement("div");
    div.className = "fav-item";
    div.innerHTML = `
      <div class="d-flex align-items-start justify-content-between">
        <div class="fw-semibold small mb-1">${escapeHtml(fav.title)}</div>
        <button class="btn btn-link btn-sm text-danger p-0 ms-2 remove-fav" data-id="${fav.id}" title="Remove">
          <i class="bi bi-trash3"></i>
        </button>
      </div>
      <div class="text-muted x-small">${new Date(fav.saved_at).toLocaleString()}</div>`;

    div.querySelector(".remove-fav").addEventListener("click", async (e) => {
      e.stopPropagation();
      await removeFavorite(fav.id);
    });

    div.addEventListener("click", (e) => {
      if (e.target.closest(".remove-fav")) return;
      appendMessage("assistant", fav.content, { showActions: true });
      bootstrap.Offcanvas.getInstance("#favoritesPanel")?.hide();
      switchTab("chat");
    });

    DOM.favoritesList.appendChild(div);
  });
}

async function saveToFavorites(content) {
  // Extract a title from the first line of content
  const firstLine = content.replace(/[#*]/g, "").split("\n")[0].trim().substring(0, 80);
  const title = firstLine || "Saved Recipe";

  try {
    const res  = await fetch("/api/favorites", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ title, content, tags: State.dietaryFilters }),
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    State.favorites.push(data.recipe);
    updateFavCount();
    showToast("Recipe saved to favorites! ⭐", "success");
  } catch (err) {
    showToast("Failed to save: " + err.message, "danger");
  }
}

async function removeFavorite(id) {
  try {
    await fetch(`/api/favorites/${id}`, { method: "DELETE" });
    State.favorites = State.favorites.filter(f => f.id !== id);
    renderFavorites();
    updateFavCount();
    showToast("Recipe removed.", "info");
  } catch (err) {
    showToast("Failed to remove: " + err.message, "danger");
  }
}

function updateFavCount() {
  const count = State.favorites.length;
  const badge = DOM.favCount;
  badge.textContent = count;
  badge.classList.toggle("d-none", count === 0);
}

// ================================================================
// Toast notifications
// ================================================================
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  const colors = { success: "bg-success", danger: "bg-danger", warning: "bg-warning text-dark", info: "bg-secondary" };

  const wrapper = document.createElement("div");
  wrapper.innerHTML = `
    <div class="toast align-items-center text-white border-0 ${colors[type] || colors.info}" role="alert">
      <div class="d-flex">
        <div class="toast-body">${escapeHtml(message)}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>
    </div>`;

  container.appendChild(wrapper);
  const toast = new bootstrap.Toast(wrapper.querySelector(".toast"), { delay: 3500 });
  toast.show();
  wrapper.querySelector(".toast").addEventListener("hidden.bs.toast", () => wrapper.remove());
}

// ================================================================
// Utilities
// ================================================================
function setButtonLoading(btn, loading) {
  btn.disabled = loading;
  btn.classList.toggle("btn-loading", loading);
}

function copyToClipboard(text, btn) {
  const plain = text.replace(/[#*`]/g, "");
  navigator.clipboard.writeText(plain).then(() => {
    btn.innerHTML = '<i class="bi bi-check me-1"></i>Copied!';
    setTimeout(() => { btn.innerHTML = '<i class="bi bi-clipboard me-1"></i>Copy'; }, 2000);
  }).catch(() => showToast("Copy failed — please copy manually.", "warning"));
}

function escapeHtml(str) {
  return (str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
