export const TYPES = ["Сайт / лендинг", "Веб-приложение"];
export const STATUSES = ["В разработке", "Завершён", "Опубликован", "Архив"];
export const SCHEMA_VERSION = 1;
export const GALLERY_MAX_IMAGES = 10;
export const GALLERY_MAX_TOTAL_DATA_CHARS = 8_000_000;
export const GALLERY_MAX_IMAGE_DATA_CHARS = 1_600_000;
export const PORTFOLIO_IMPORT_MAX_BYTES = 64 * 1024 * 1024;
export const PORTFOLIO_IMPORT_MAX_COVER_BYTES = 2 * 1024 * 1024;
export const PORTFOLIO_IMPORT_MAX_IMAGE_PIXELS = 24_000_000;
export const PORTFOLIO_IMPORT_MAX_PROJECTS = 130_000;
export const PORTFOLIO_IMPORT_MAX_IMAGES = 250;
export const PORTFOLIO_IMPORT_MAX_IMAGE_DATA_CHARS = 24_000_000;
export const PORTFOLIO_IMPORT_MAX_TOTAL_IMAGE_PIXELS = 120_000_000;

const BUILTIN_COVER_REFRESH = new Map([
  ["./assets/covers/cleaning-crm.webp", "./assets/covers/cleaning-crm-case-v2.webp"],
  ["./assets/covers/city-courtyards.webp", "./assets/covers/city-courtyards-case-v2.webp"],
  ["./assets/covers/cleaning-crm.png", "./assets/covers/cleaning-crm-case-v2.webp"],
  ["./assets/covers/city-courtyards.png", "./assets/covers/city-courtyards-case-v2.webp"],
  ["./assets/covers/portfolio-studio.png", "./assets/covers/portfolio-studio.webp"],
]);

export function resolveCoverImageSource(source) {
  const path = String(source ?? "");
  return BUILTIN_COVER_REFRESH.get(path) || path;
}

function embeddedBase64ByteLength(dataUrl) {
  const payload = dataUrl.slice(dataUrl.indexOf(",") + 1);
  const padding = payload.endsWith("==") ? 2 : payload.endsWith("=") ? 1 : 0;
  return Math.floor(payload.length * 3 / 4) - padding;
}

export async function readPortfolioFile(file) {
  if (!file || typeof file.text !== "function" || !Number.isFinite(file.size)) {
    throw new Error("Не удалось прочитать выбранный файл.");
  }
  if (file.size > PORTFOLIO_IMPORT_MAX_BYTES) {
    throw new Error("Резервная копия больше 64 МиБ. Выберите файл меньшего размера.");
  }
  return file.text();
}

export async function validatePortfolioImages(portfolio, createImage = () => new Image()) {
  if (!portfolio || !Array.isArray(portfolio.projects)) throw new Error("Не удалось проверить изображения портфолио.");
  let imageCount = 0, imageDataChars = 0, totalPixels = 0;
  for (const project of portfolio.projects) {
    const images = [
      ...(project.cover_image_data ? [[project.cover_image_data, `Обложка проекта «${project.title}»`]] : []),
      ...(project.gallery_images || []).map((image, index) => [image.image_data, `Изображение №${index + 1} проекта «${project.title}»`]),
    ];
    for (const [data, label] of images) {
      imageCount++;
      imageDataChars += data.length;
      if (imageCount > PORTFOLIO_IMPORT_MAX_IMAGES) throw new Error(`В резервной копии может быть не больше ${PORTFOLIO_IMPORT_MAX_IMAGES} изображений.`);
      if (imageDataChars > PORTFOLIO_IMPORT_MAX_IMAGE_DATA_CHARS) throw new Error("Общий размер изображений в резервной копии превышает 24 млн символов (около 18 МиБ медиа).");
      const image = createImage();
      try {
        image.src = data;
        try { await image.decode(); }
        catch { throw new Error(`${label}: изображение повреждено или не читается.`); }
        const pixels = Number(image.naturalWidth) * Number(image.naturalHeight);
        if (!Number.isFinite(pixels) || pixels <= 0) throw new Error(`${label}: изображение повреждено или не читается.`);
        if (pixels > PORTFOLIO_IMPORT_MAX_IMAGE_PIXELS) throw new Error(`${label}: разрешение превышает 24 мегапикселя.`);
        totalPixels += pixels;
        if (totalPixels > PORTFOLIO_IMPORT_MAX_TOTAL_IMAGE_PIXELS) throw new Error("Суммарное разрешение изображений в резервной копии превышает 120 мегапикселей.");
      } finally {
        image.removeAttribute?.("src");
      }
    }
  }
}

export async function inspectBrowserStorage(storage = globalThis.navigator?.storage) {
  if (!storage) return { supported: false, persistentSupported: false, persistent: null, usage: null, quota: null };
  const [estimate, persisted] = await Promise.all([
    typeof storage.estimate === "function"
      ? Promise.resolve().then(() => storage.estimate()).catch(() => null)
      : Promise.resolve(null),
    typeof storage.persisted === "function"
      ? Promise.resolve().then(() => storage.persisted()).catch(() => null)
      : Promise.resolve(null),
  ]);
  const finiteOrNull = value => Number.isFinite(value) ? value : null;
  return {
    supported: typeof storage.estimate === "function",
    persistentSupported: typeof storage.persisted === "function" && typeof storage.persist === "function",
    persistent: typeof persisted === "boolean" ? persisted : null,
    usage: finiteOrNull(estimate?.usage),
    quota: finiteOrNull(estimate?.quota),
  };
}

export async function requestPersistentBrowserStorage(storage = globalThis.navigator?.storage) {
  if (typeof storage?.persisted !== "function" || typeof storage?.persist !== "function") {
    return { supported: false, granted: false, already: false, error: false };
  }
  try {
    if (await storage.persisted()) return { supported: true, granted: true, already: true, error: false };
    return { supported: true, granted: (await storage.persist()) === true, already: false, error: false };
  } catch {
    return { supported: true, granted: false, already: false, error: true };
  }
}

export function normalizeTags(value) {
  const values = Array.isArray(value) ? value : typeof value === "string" ? value.split(",") : value == null ? [] : null;
  if (!values) throw new Error("Теги должны быть списком или строкой.");
  const tags = [], seen = new Set();
  for (const item of values) {
    if (typeof item !== "string") throw new Error("Каждый тег должен быть текстом.");
    const tag = item.trim();
    if (!tag) continue;
    if (tag.length > 32 || /[\u0000-\u001f\u007f]/.test(tag)) throw new Error("Тег должен содержать до 32 символов без управляющих знаков.");
    const key = tag.toLocaleLowerCase("ru");
    if (seen.has(key)) continue;
    seen.add(key); tags.push(tag);
    if (tags.length > 20) throw new Error("У проекта может быть не больше 20 тегов.");
  }
  return tags;
}

function normalizeCaseText(value, label, limit) {
  if (value == null) return "";
  if (typeof value !== "string") throw new Error(`Поле «${label}» должно быть текстом.`);
  const text = value.trim();
  if (text.length > limit) throw new Error(`Поле «${label}» должно содержать не больше ${limit} символов.`);
  if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(text)) throw new Error(`Поле «${label}» содержит управляющие символы.`);
  return text;
}

export function normalizeProject(row, index = 0) {
  if (!row || typeof row !== "object" || Array.isArray(row)) throw new Error(`Запись №${index + 1} должна быть объектом.`);
  const title = normalizeCaseText(row.title, "Название", 90);
  const description = normalizeCaseText(row.description, "Короткое описание", 500);
  const type = String(row.type ?? row.project_type ?? "");
  const id = row.id ?? row.project_id ?? index + 1;
  if (!title || !description) throw new Error(`У проекта №${index + 1} заполните название и описание.`);
  if (typeof id !== "number" || !Number.isSafeInteger(id) || id < 1) throw new Error(`У проекта «${title}» некорректный ID.`);
  const sortOrder = row.sort_order ?? id;
  if (typeof sortOrder !== "number" || !Number.isSafeInteger(sortOrder) || sortOrder < 1) throw new Error(`У проекта «${title}» порядок должен быть положительным целым числом.`);
  if (!TYPES.includes(type)) throw new Error(`У проекта «${title}» неизвестный тип.`);
  const createdAt = String(row.created_at ?? "");
  const dateParts = /^(\d{4})-(\d{2})-(\d{2})$/.exec(createdAt);
  const parsedDate = dateParts && new Date(0);
  if (parsedDate) parsedDate.setUTCFullYear(+dateParts[1], +dateParts[2] - 1, +dateParts[3]);
  if (!dateParts || +dateParts[1] < 1 || parsedDate.toISOString().slice(0, 10) !== createdAt) {
    throw new Error(`У проекта «${title}» дата должна иметь формат ГГГГ-ММ-ДД.`);
  }
  const status = String(row.status ?? "Завершён");
  if (!STATUSES.includes(status)) throw new Error(`У проекта «${title}» неизвестный статус.`);
  const priorTechnologyDetails = new Map((Array.isArray(row.technology_details) ? row.technology_details : [])
    .filter((item) => item && typeof item.name === "string")
    .map((item) => [item.name.toLocaleLowerCase("ru"), item]));
  const technologyDetails = Array.isArray(row.technologies)
    ? row.technologies.map((item) => {
      if (typeof item === "string") {
        const name = item.trim();
        const saved = priorTechnologyDetails.get(name.toLocaleLowerCase("ru"));
        return name ? {
          name,
          category: typeof saved?.category === "string" && saved.category.trim() ? saved.category.trim() : "Инструмент",
          version: typeof saved?.version === "string" ? saved.version.trim() : "",
        } : null;
      }
      const name = String(item?.name ?? "").trim();
      return name ? {
        name,
        category: typeof item?.category === "string" && item.category.trim() ? item.category.trim() : "Инструмент",
        version: typeof item?.version === "string" ? item.version.trim() : "",
      } : null;
    }).filter(Boolean)
    : [];
  if (technologyDetails.length > 40) throw new Error(`У проекта «${title}» может быть не больше 40 технологий.`);
  for (const [technologyIndex, technology] of technologyDetails.entries()) {
    technology.name = normalizeCaseText(technology.name, `Название технологии №${technologyIndex + 1}`, 60);
    technology.category = normalizeCaseText(technology.category, `Категория технологии №${technologyIndex + 1}`, 60) || "Инструмент";
    technology.version = normalizeCaseText(technology.version, `Версия технологии №${technologyIndex + 1}`, 40);
  }
  const technologies = technologyDetails.map((item) => item.name);
  const pageCount = row.page_count ?? 1;
  if (type === TYPES[0] && (typeof pageCount !== "number" || !Number.isSafeInteger(pageCount) || pageCount < 1)) throw new Error(`У проекта «${title}» количество страниц должно быть положительным целым числом.`);
  const project = {
    id, sort_order: sortOrder, type, title, description, created_at: createdAt, status, technologies,
    technology_details: technologyDetails,
    demo_url: normalizeUrl(row.demo_url ?? "", `Демо проекта «${title}»`),
    role: normalizeCaseText(row.role, "Ваша роль", 120), outcome: normalizeCaseText(row.outcome, "Результат", 500),
    context: normalizeCaseText(row.context, "Контекст задачи", 500),
    solution: normalizeCaseText(row.solution, "Решение", 700),
    process: normalizeCaseText(row.process, "Этапы процесса", 1500),
    metrics: normalizeCaseText(row.metrics, "Метрики результата", 300), tags: normalizeTags(row.tags),
    featured: row.featured ?? false,
  };
  if (typeof project.featured !== "boolean") throw new Error(`Поле «В избранном» проекта «${title}» должно быть логическим значением.`);
  const coverImage = String(row.cover_image ?? "").trim();
  if (coverImage && !/^\.\/assets\/covers\/[a-z0-9-]+\.(?:png|webp|jpe?g)$/i.test(coverImage)) {
    throw new Error(`У проекта «${title}» обложка должна ссылаться на локальный файл в assets/covers.`);
  }
  if (coverImage) project.cover_image = coverImage;
  const coverPosition = String(row.cover_position ?? "50% 46%");
  if (!/^(?:100|[0-9]{1,2})% (?:100|[0-9]{1,2})%$/.test(coverPosition)) {
    throw new Error(`У проекта «${title}» некорректная точка кадрирования обложки.`);
  }
  project.cover_position = coverPosition;
  const rawMobileCoverPosition = row.cover_position_mobile;
  if (rawMobileCoverPosition != null && String(rawMobileCoverPosition).trim() !== "") {
    const coverPositionMobile = String(rawMobileCoverPosition).trim();
    if (!/^(?:100|[0-9]{1,2})% (?:100|[0-9]{1,2})%$/.test(coverPositionMobile)) {
      throw new Error(`У проекта «${title}» некорректная точка кадрирования обложки для телефона.`);
    }
    project.cover_position_mobile = coverPositionMobile;
  }
  const coverImageData = String(row.cover_image_data ?? "").trim();
  if (coverImageData && (coverImageData.length > 2_800_000
    || !/^data:image\/(?:png|jpeg|webp);base64,[A-Za-z0-9+/]+={0,2}$/.test(coverImageData))) {
    throw new Error(`У проекта «${title}» обложка должна быть PNG, JPEG или WebP до 2 МиБ.`);
  }
  if (coverImageData && embeddedBase64ByteLength(coverImageData) > PORTFOLIO_IMPORT_MAX_COVER_BYTES) {
    throw new Error(`У проекта «${title}» обложка должна быть не больше 2 МиБ.`);
  }
  if (coverImageData) project.cover_image_data = coverImageData;
  const galleryImages = row.gallery_images ?? [];
  if (!Array.isArray(galleryImages) || galleryImages.length > GALLERY_MAX_IMAGES) throw new Error(`У проекта «${title}» может быть не больше ${GALLERY_MAX_IMAGES} дополнительных изображений.`);
  if (galleryImages.reduce((total, image) => total + (typeof image?.image_data === "string" ? image.image_data.length : 0), 0) > GALLERY_MAX_TOTAL_DATA_CHARS) throw new Error(`Общий размер галереи проекта «${title}» превышает лимит 8 млн символов (около 6 МиБ медиа).`);
  project.gallery_images = galleryImages.map((image, imageIndex) => {
    if (!image || typeof image !== 'object' || Array.isArray(image)) throw new Error(`Изображение №${imageIndex + 1} должно быть объектом.`);
    const imageData = String(image.image_data ?? '').trim(), alt = normalizeCaseText(image.alt, `Описание изображения №${imageIndex + 1}`, 180);
    const position = String(image.position ?? '50% 50%');
    if (!/^data:image\/(?:png|jpeg|webp);base64,[A-Za-z0-9+/]+={0,2}$/.test(imageData) || imageData.length > GALLERY_MAX_IMAGE_DATA_CHARS)
      throw new Error(`Изображение №${imageIndex + 1} должно быть PNG, JPEG или WebP размером до 1,2 МиБ.`);
    if (!alt) throw new Error(`Добавьте текстовое описание для изображения №${imageIndex + 1}.`);
    if (!/^(?:100|[0-9]{1,2})% (?:100|[0-9]{1,2})%$/.test(position)) throw new Error(`У изображения №${imageIndex + 1} некорректная точка кадрирования.`);
    return { image_data: imageData, alt, position };
  });
  if (type === TYPES[0]) project.page_count = pageCount;
  if (type === TYPES[1]) {
    project.repository_url = normalizeUrl(row.repository_url ?? "", `Репозиторий проекта «${title}»`);
    project.backend_stack = normalizeCaseText(row.backend_stack, "Серверная часть", 180);
  }
  return project;
}

export function normalizeUrl(value, label = "Ссылка") {
  const text = String(value ?? "").trim();
  if (!text) return "";
  let url;
  try { url = new URL(text); } catch { throw new Error(`${label}: укажите полный адрес, начинающийся с https:// или http://.`); }
  if (!["http:", "https:"].includes(url.protocol) || !url.hostname || url.username || url.password) {
    throw new Error(`${label}: разрешены только ссылки HTTP и HTTPS без логина и пароля.`);
  }
  return url.href;
}

export function parsePortfolioFile(text) {
  let raw;
  try { raw = JSON.parse(text); } catch { throw new Error("Файл не является корректным JSON."); }
  if (!raw || typeof raw !== "object" || !Array.isArray(raw.projects)) throw new Error("В JSON должен быть список projects.");
  const schemaVersion = raw.schema_version == null ? 1 : raw.schema_version;
  if (!Number.isSafeInteger(schemaVersion) || schemaVersion < 1) throw new Error("В резервной копии указана некорректная версия формата.");
  if (schemaVersion > SCHEMA_VERSION) throw new Error("Этот файл создан более новой версией приложения.");
  if (raw.projects.length > PORTFOLIO_IMPORT_MAX_PROJECTS) throw new Error(`В резервной копии может быть не больше ${PORTFOLIO_IMPORT_MAX_PROJECTS} проектов.`);
  const declaredNextId = raw.next_id == null ? 1 : raw.next_id;
  if (!Number.isSafeInteger(declaredNextId) || declaredNextId < 1) throw new Error("В резервной копии указан некорректный следующий ID проекта.");
  let importedImageCount = 0, importedImageDataChars = 0;
  for (const item of raw.projects) {
    if (!item || typeof item !== "object" || Array.isArray(item)) continue;
    const images = [item.cover_image_data, ...(Array.isArray(item.gallery_images) ? item.gallery_images.map(image => image?.image_data) : [])].filter(value => typeof value === "string" && value.length > 0);
    importedImageCount += images.length;
    importedImageDataChars += images.reduce((total, data) => total + data.length, 0);
    if (importedImageCount > PORTFOLIO_IMPORT_MAX_IMAGES) throw new Error(`В резервной копии может быть не больше ${PORTFOLIO_IMPORT_MAX_IMAGES} изображений.`);
    if (importedImageDataChars > PORTFOLIO_IMPORT_MAX_IMAGE_DATA_CHARS) throw new Error("Общий размер изображений в резервной копии превышает 24 млн символов (около 18 МиБ медиа).");
  }
  const projects = raw.projects.map((item, index) => normalizeProject(item, index));
  const ids = new Set(projects.map((project) => project.id));
  if (ids.size !== projects.length) throw new Error("В файле повторяются идентификаторы проектов.");
  const developer = normalizeDeveloper(raw.developer);
  const nextId = projects.reduce((maximum, project) => Math.max(maximum, project.id + 1), declaredNextId);
  if (!Number.isSafeInteger(nextId)) throw new Error("ID проекта достиг предельного значения. Обновите резервную копию вручную.");
  const title = normalizeCaseText(raw.title ?? "Портфолио веб-разработчика", "Название портфолио", 120) || "Портфолио веб-разработчика";
  return {
    schema_version: SCHEMA_VERSION,
    title,
    next_id: nextId,
    developer,
    projects,
  };
}

export function normalizeDeveloper(raw = {}) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw new Error("Профиль автора должен быть объектом.");
  const limits = { full_name: 90, specialization: 90, introduction: 800, email: 254, website_url: 300, github_url: 300 };
  const fallback = { full_name: "Ваше имя", specialization: "Веб-разработчик", introduction: "", email: "", website_url: "", github_url: "" };
  const profile = {};
  for (const [key, max] of Object.entries(limits)) {
    const value = raw[key] ?? fallback[key];
    if (typeof value !== "string") throw new Error(`Поле профиля «${key}» должно быть текстом.`);
    const normalized = value.trim();
    if (normalized.length > max) throw new Error(`Поле профиля «${key}» не должно превышать ${max} символов.`);
    if ([...normalized].some((char) => (char.charCodeAt(0) < 32 && !"\n\t".includes(char)) || char.charCodeAt(0) === 127))
      throw new Error(`Поле профиля «${key}» содержит управляющие символы.`);
    profile[key] = normalized;
  }
  if (!profile.full_name || !profile.specialization) throw new Error("Имя и специализация автора обязательны.");
  if (profile.email && !/^[^\s@<>]+@[^\s@<>.]+(?:\.[^\s@<>.]+)+$/.test(profile.email)) throw new Error("Введите корректный email автора.");
  for (const key of ["website_url", "github_url"]) {
    if (!profile[key]) continue;
    let url;
    try { url = new URL(profile[key]); } catch { throw new Error(`Поле профиля «${key}» должно быть ссылкой HTTP или HTTPS.`); }
    if (!(["http:", "https:"].includes(url.protocol)) || !url.hostname || url.username || url.password)
      throw new Error(`Поле профиля «${key}» должно быть ссылкой HTTP или HTTPS без логина и пароля.`);
    profile[key] = url.href;
  }
  for (const key of ["include_email", "include_website", "include_github"]) {
    if (raw[key] !== undefined && typeof raw[key] !== "boolean") throw new Error(`Поле профиля «${key}» должно быть логическим значением.`);
    profile[key] = raw[key] === true;
  }
  return profile;
}

function portfolioNextId(projects, requested = 1) {
  if (!Number.isSafeInteger(requested) || requested < 1) throw new Error("Указан некорректный следующий ID проекта.");
  let maximum = 0;
  for (const project of projects) maximum = Math.max(maximum, project.id);
  const nextId = Math.max(requested, maximum + 1);
  if (!Number.isSafeInteger(nextId)) throw new Error("ID проекта достиг предельного значения. Обновите резервную копию вручную.");
  return nextId;
}

export function serializePortfolio(model) {
  if (!Array.isArray(model.projects) || model.projects.length > PORTFOLIO_IMPORT_MAX_PROJECTS) {
    throw new Error(`В портфолио может быть не больше ${PORTFOLIO_IMPORT_MAX_PROJECTS} проектов.`);
  }
  const projects = model.projects.map((p) => ({
      id: p.id, project_id: p.id, sort_order: p.sort_order, type: p.type, title: p.title, description: p.description,
      created_at: p.created_at, status: p.status,
      technologies: (p.technology_details || p.technologies.map((name) => ({ name, category: "Инструмент", version: "" })))
        .map(({ name, category, version }) => ({ name, category: category || "Инструмент", version: version || "" })),
      demo_url: p.demo_url, role: p.role, outcome: p.outcome, context: p.context,
      solution: p.solution, process: p.process, metrics: p.metrics, tags: p.tags, featured: p.featured,
      ...(p.cover_image ? { cover_image: p.cover_image } : {}),
      ...(p.cover_image_data ? { cover_image_data: p.cover_image_data } : {}),
      cover_position: p.cover_position || "50% 46%",
      ...(p.cover_position_mobile ? { cover_position_mobile: p.cover_position_mobile } : {}),
      gallery_images: p.gallery_images,
      ...(p.type === TYPES[0] ? { page_count: p.page_count } : { repository_url: p.repository_url, backend_stack: p.backend_stack }),
    }));
  projects.forEach((project, index) => normalizeProject(project, index));
  const nextId = portfolioNextId(projects, model.next_id ?? 1);
  let imageCount = 0, imageDataChars = 0;
  for (const project of projects) {
    const images = [project.cover_image_data, ...(project.gallery_images || []).map(image => image?.image_data)]
      .filter(value => typeof value === "string" && value.length > 0);
    imageCount += images.length;
    imageDataChars += images.reduce((sum, value) => sum + value.length, 0);
    if (imageCount > PORTFOLIO_IMPORT_MAX_IMAGES) throw new Error(`В портфолио может быть не больше ${PORTFOLIO_IMPORT_MAX_IMAGES} изображений.`);
    if (imageDataChars > PORTFOLIO_IMPORT_MAX_IMAGE_DATA_CHARS) throw new Error("Общий размер изображений превышает лимит 24 млн символов.");
  }
  return {
    schema_version: SCHEMA_VERSION,
    title: model.title || "Портфолио веб-разработчика",
    next_id: nextId,
    developer: normalizeDeveloper(model.developer),
    projects,
  };
}

export function serializePortfolioFile(model, maxBytes = PORTFOLIO_IMPORT_MAX_BYTES) {
  const text = JSON.stringify(serializePortfolio(model), null, 2);
  if (new TextEncoder().encode(text).byteLength > maxBytes) {
    throw new Error("Резервная копия превысит 64 МиБ. Сократите данные или количество изображений перед экспортом.");
  }
  return text;
}

export function filterProjects(projects, { query = "", type = "Все типы", status = "Все статусы", tag = "Все теги", featuredOnly = false, sort = "featured" } = {}) {
  const q = query.trim().toLocaleLowerCase("ru");
  const filtered = projects.filter((p) => {
    const searchText = [p.title, p.description, p.status, p.type, p.created_at, p.role, p.outcome,
      p.demo_url, p.repository_url, p.backend_stack, p.page_count, p.context, p.solution, p.process, p.metrics,
      ...p.technologies, ...p.tags].join(" ").toLocaleLowerCase("ru");
    return (!q || searchText.includes(q)) && (type === "Все типы" || p.type === type)
      && (status === "Все статусы" || p.status === status)
      && (tag === "Все теги" || p.tags.some((value) => value.toLocaleLowerCase("ru") === tag.toLocaleLowerCase("ru")))
      && (!featuredOnly || p.featured);
  });
  const sorters = {
    featured: (a, b) => Number(b.featured) - Number(a.featured) || a.sort_order - b.sort_order || a.title.localeCompare(b.title, "ru"),
    order: (a, b) => a.sort_order - b.sort_order || a.id - b.id,
    title: (a, b) => a.title.localeCompare(b.title, "ru"),
    tags: (a, b) => {
      const tagKey = (project) => project.tags
        .map((value) => value.toLocaleLowerCase("ru"))
        .sort((left, right) => left.localeCompare(right, "ru"))
        .join("\u0000");
      const left = tagKey(a);
      const right = tagKey(b);
      if (!left || !right) return Number(!left) - Number(!right) || a.title.localeCompare(b.title, "ru");
      return left.localeCompare(right, "ru") || a.title.localeCompare(b.title, "ru");
    },
    newest: (a, b) => b.created_at.localeCompare(a.created_at),
    oldest: (a, b) => a.created_at.localeCompare(b.created_at),
  };
  return filtered.sort(sorters[sort] || sorters.featured);
}

export function moveProject(projects, id, direction) {
  if (direction !== -1 && direction !== 1) throw new Error("Направление перемещения должно быть -1 или 1.");
  const project = projects.find((item) => item.id === Number(id));
  if (!project) return false;
  const peers = projects.filter((item) => item.featured === project.featured)
    .sort((a, b) => a.sort_order - b.sort_order || a.id - b.id);
  const target = peers[peers.indexOf(project) + direction];
  if (!target) return false;
  [project.sort_order, target.sort_order] = [target.sort_order, project.sort_order];
  return true;
}

export function duplicateProject(projects, id, createdAt = new Date().toISOString().slice(0, 10), requestedNextId = 1) {
  const source = projects.find((item) => item.id === Number(id));
  if (!source) return null;
  const duplicate = structuredClone(source);
  duplicate.id = portfolioNextId(projects, requestedNextId);
  if (!Number.isSafeInteger(duplicate.id + 1)) throw new Error("ID проекта достиг предельного значения. Обновите резервную копию вручную.");
  duplicate.sort_order = Math.max(0, ...projects.filter((item) => !item.featured).map((item) => item.sort_order || item.id)) + 1;
  duplicate.title = `${source.title.slice(0, 82).trimEnd()} — копия`;
  duplicate.created_at = createdAt;
  duplicate.demo_url = "";
  if (duplicate.type === TYPES[1]) duplicate.repository_url = "";
  duplicate.featured = false;
  const normalized = normalizeProject(duplicate, projects.length);
  projects.push(normalized);
  return normalized;
}

export function previewPortfolioImport(currentProjects, incomingProjects) {
  const current = new Map(currentProjects.map((project) => [project.id, project]));
  const conflicts = incomingProjects.flatMap((project) => current.has(project.id)
    ? [{ id: project.id, currentTitle: current.get(project.id).title, incomingTitle: project.title }]
    : []);
  return { incoming: incomingProjects.length, current: currentProjects.length, conflicts, additions: incomingProjects.length - conflicts.length };
}

export function mergePortfolioImport(currentProjects, incomingProjects, strategy = "keep-current", currentNextId = 1, incomingNextId = 1) {
  if (!["keep-current", "replace", "copy"].includes(strategy)) throw new Error("Неизвестная стратегия импорта.");
  const projects = currentProjects.map((project) => structuredClone(project));
  const currentById = new Map(projects.map((project, index) => [project.id, index]));
  const localPosition = new Map([...currentProjects].sort((a, b) => a.sort_order - b.sort_order || a.id - b.id).map((project, index) => [project.id, index]));
  const importPosition = new Map();
  const stats = { added: 0, replaced: 0, skipped: 0, copied: 0 };
  let nextId = portfolioNextId([...projects, ...incomingProjects], Math.max(currentNextId, incomingNextId));
  for (const incoming of incomingProjects) {
    const conflictIndex = currentById.get(incoming.id);
    if (conflictIndex !== undefined && strategy === "keep-current") {
      stats.skipped++;
      continue;
    }
    if (conflictIndex !== undefined && strategy === "replace") {
      projects[conflictIndex] = structuredClone(incoming);
      stats.replaced++;
      continue;
    }
    const project = structuredClone(incoming);
    if (conflictIndex !== undefined) {
      project.id = nextId++;
      project.title = `${project.title.slice(0, 81).trimEnd()} — импорт`;
      stats.copied++;
    } else {
      stats.added++;
    }
    projects.push(project);
    importPosition.set(project.id, importPosition.size);
  }
  for (const featured of [true, false]) {
    projects.filter((project) => project.featured === featured)
      .sort((a, b) => {
        const aLocal = localPosition.get(a.id), bLocal = localPosition.get(b.id);
        if (aLocal !== undefined && bLocal !== undefined) return aLocal - bLocal;
        if (aLocal !== undefined) return -1;
        if (bLocal !== undefined) return 1;
        return (importPosition.get(a.id) ?? Infinity) - (importPosition.get(b.id) ?? Infinity) || a.sort_order - b.sort_order || a.id - b.id;
      })
      .forEach((project, index) => { project.sort_order = index + 1; });
  }
  return { projects, nextId, stats };
}

export function restoreProjectsWithUniqueIds(currentProjects, removedItems, requestedNextId = 1) {
  const projects = currentProjects.map((project) => structuredClone(project));
  let nextId = portfolioNextId(projects, requestedNextId);
  const restored = [];
  for (const item of [...removedItems].sort((a, b) => a.index - b.index)) {
    const project = structuredClone(item.project);
    const originalId = project.id;
    if (projects.some((candidate) => candidate.id === project.id)) {
      project.id = nextId;
      if (!Number.isSafeInteger(project.id + 1)) throw new Error("Не удалось восстановить проект: достигнут предел ID.");
      nextId++;
    } else {
      nextId = portfolioNextId([...projects, project], nextId);
    }
    projects.splice(Math.min(item.index, projects.length), 0, project);
    restored.push({ originalId, project });
  }
  return { projects, nextId, restored };
}

export function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}

export function caseCountLabel(value) {
  const count = Math.max(0, Math.trunc(Number(value) || 0));
  const lastTwo = count % 100, last = count % 10;
  const noun = last === 1 && lastTwo !== 11 ? "избранный кейс"
    : last >= 2 && last <= 4 && (lastTwo < 12 || lastTwo > 14) ? "избранных кейса" : "избранных кейсов";
  return `${count} ${noun}`;
}

export function showcaseExportSummary(model) {
  const developer = normalizeDeveloper(model?.developer);
  const projects = (model?.projects || []).filter((project) => project?.featured === true);
  const contacts = [
    developer.include_email && developer.email ? { label: "Email", value: developer.email } : null,
    developer.include_website && developer.website_url ? { label: "Личный сайт", value: developer.website_url } : null,
    developer.include_github && developer.github_url ? { label: "GitHub", value: developer.github_url } : null,
  ].filter(Boolean);
  return {
    author: developer.full_name,
    specialization: developer.specialization,
    introduction: developer.introduction,
    contacts,
    projects: projects.map((project) => ({
      title: project.title,
      links: [project.demo_url, project.repository_url].filter(Boolean),
      images: 1 + (Array.isArray(project.gallery_images) ? project.gallery_images.length : 0),
    })),
  };
}

export function staticShowcaseExport(model, covers = {}, options = {}) {
  const theme = ["editorial", "night", "gallery"].includes(options?.theme) ? options.theme : "editorial";
  const themeCss = theme === "night" ? `
:root{color-scheme:dark;color:#F3F5F1;background:#141816}body{background:#141816;color:#F3F5F1}.masthead,.footer{border-color:#39433D;color:#B9C3BB}.local,.intro p,.description,.story p,.facts p,.empty p{color:#B9C3BB}.eyebrow,.story h3,.facts h3,.empty>span{color:#B9D6A8}.count{background:#2C4331;color:#DDF3D3}.project{background:#202722;border-color:#39443C;box-shadow:0 18px 50px #0005}.cover{background:#29352E}.meta{color:#C0CAC2}.facts{border-color:#39443C}.tags span{background:#2C3C32;color:#D8EAD8}.links a{color:#D7ECD8;border-color:#536553}.links a:hover{background:#2B3B30}.empty{border-color:#536553}
` : theme === "gallery" ? `
:root{color-scheme:light;color:#1D2923;background:#FFFFFF}body{background:#FFFFFF}.masthead,.footer{border-color:#E6EBE7}.intro{max-width:none;text-align:center;padding:76px 0 48px}.intro p{max-width:720px;margin:0 auto}.intro h1{letter-spacing:-.045em}.projects{grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}.project{grid-template-columns:1fr;border-radius:18px;box-shadow:0 12px 34px #24352a12}.cover{height:280px;min-height:280px}.project-content{padding:28px}.facts{grid-template-columns:1fr}.count{background:#E9F4EA;color:#245D37}.links a{background:#F6FAF6}@media(max-width:700px){.projects{grid-template-columns:1fr}.cover{height:240px;min-height:240px}.intro{padding:52px 0 36px}}
` : "";
  const title = escapeHtml(model.title || "Портфолио");
  const developer = normalizeDeveloper(model.developer);
  const name = escapeHtml(developer.full_name || "Автор портфолио");
  const specialization = escapeHtml(developer.specialization || "Веб-разработчик");
  const introduction = escapeHtml(developer.introduction || "Избранные проекты, решения и результаты.").replaceAll("\n", "<br>");
  const contacts = [
    developer.include_email && developer.email ? [`mailto:${developer.email}`, "Написать на email"] : null,
    developer.include_website && developer.website_url ? [developer.website_url, "Личный сайт"] : null,
    developer.include_github && developer.github_url ? [developer.github_url, "GitHub"] : null,
  ].filter(Boolean).map(([href, label]) => `<a href="${escapeHtml(href)}"${href.startsWith("https:") || href.startsWith("http:") ? ' target="_blank" rel="noopener noreferrer"' : ""}>${label}</a>`).join("");
  const projects = filterProjects(model.projects || [], { sort: "featured" }).filter((project) => project.featured);
  const projectMarkup = projects.map((p, index) => {
    const cover = String(covers[p.id] || p.cover_image_data || "");
    const image = /^data:image\/(?:png|jpeg|webp);base64,[A-Za-z0-9+/]+={0,2}$/.test(cover)
      ? `<img class="cover" src="${cover}" alt="Иллюстрация: ${escapeHtml(p.title)}" style="--cover-position:${escapeHtml(p.cover_position || "50% 46%")};--cover-position-mobile:${escapeHtml(p.cover_position_mobile || p.cover_position || "50% 46%")}"${index ? ' loading="lazy"' : ''}>`
      : `<div class="cover cover-placeholder" aria-hidden="true"><span>${String(index + 1).padStart(2, "0")}</span></div>`;
    const story = [["Контекст", p.context], ["Решение", p.solution], ["Процесс", p.process], ["Результат", p.outcome], ["Метрики", p.metrics]]
      .filter(([, value]) => value)
      .map(([label, value]) => `<section class="story"><h3>${label}</h3><p>${escapeHtml(value).replaceAll("\n", "<br>")}</p></section>`).join("");
    const gallery = (p.gallery_images || []).map((item, imageIndex) => `<figure style="margin:0;overflow:hidden;border-radius:12px;background:#edf0e9"><img src="${escapeHtml(item.image_data)}" alt="${escapeHtml(item.alt)}" style="display:block;width:100%;height:260px;object-fit:cover;object-position:${escapeHtml(item.position)}"${imageIndex ? ' loading="lazy"' : ''}><figcaption style="padding:10px 12px;color:#53635b;font-size:12px">${escapeHtml(item.alt)}</figcaption></figure>`).join("");
    const links = [["Демо проекта", p.demo_url], ["Исходный код", p.repository_url]]
      .filter(([, href]) => /^https?:\/\//i.test(href || ""))
      .map(([label, href]) => `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${label}<span aria-hidden="true"> ↗</span></a>`).join("");
    const facts = [["Моя роль", p.role], ["Технологии", (p.technologies || []).join(" · ")]]
      .filter(([, value]) => String(value || "").trim())
      .map(([label, value]) => `<div><h3>${label}</h3><p>${escapeHtml(value)}</p></div>`).join("");
    return `<article class="project">${image}<div class="project-content"><div class="meta"><span>${escapeHtml(p.type)}</span><span>${escapeHtml(p.status)}</span></div><h2>${escapeHtml(p.title)}</h2><p class="description">${escapeHtml(p.description)}</p>${story}${gallery ? `<section class="portfolio-gallery" aria-label="Галерея проекта"><h3>В деталях</h3><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:12px">${gallery}</div></section>` : ""}${facts ? `<section class="facts" aria-label="Сведения о проекте">${facts}</section>` : ""}${p.tags?.length ? `<p class="tags">${p.tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}</p>` : ""}${links ? `<nav class="links" aria-label="Ссылки проекта">${links}</nav>` : ""}</div></article>`;
  }).join("");
  const empty = `<div class="empty"><span aria-hidden="true">✳</span><h2>Витрина готовится</h2><p>Автор пока не выбрал проекты для публикации.</p></div>`;
  return `<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light"><meta name="description" content="Портфолио ${name} — ${specialization}"><title>${title} — ${name}</title>
<style>
:root{font-family:Inter,"Segoe UI",Arial,sans-serif;color:#17231f;background:#f3f1e9;font-synthesis:none;text-rendering:optimizeLegibility;-webkit-font-smoothing:antialiased}*{box-sizing:border-box}body{margin:0}.wrap{width:min(1100px,calc(100% - 40px));margin:auto}.masthead{padding:28px 0;border-bottom:1px solid #d9d8cd;display:flex;justify-content:space-between;align-items:center;gap:20px}.brand{font-weight:800;letter-spacing:-.04em}.local{font-size:12px;color:#53635b}.intro{padding:88px 0 64px;max-width:790px}.eyebrow,.story h3,.facts h3{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#527264}.intro h1{font-size:clamp(44px,8vw,88px);line-height:.98;letter-spacing:-.07em;margin:18px 0}.intro p{font-size:clamp(18px,2.5vw,24px);line-height:1.5;color:#53635b;margin:0}.count{display:inline-flex;margin-top:28px;padding:9px 13px;border-radius:999px;background:#e1e9dc;color:#2e5942;font-size:12px;font-weight:700}.projects{display:grid;gap:30px;padding:0 0 80px}.project{display:grid;grid-template-columns:minmax(260px,.82fr) 1.18fr;background:#fff;border:1px solid #e5e4da;border-radius:22px;overflow:hidden;box-shadow:0 18px 50px #28392d0a}.cover{width:100%;height:100%;min-height:380px;object-fit:cover;object-position:var(--cover-position,50% 46%);background:#d7e2d4}.cover-placeholder{display:flex;align-items:flex-end;padding:28px;background:radial-gradient(ellipse at 75% 20%,#d7e6cf 0,transparent 35%),linear-gradient(140deg,#203f35,#a8b89b);color:#fff}.cover-placeholder span{font-size:90px;font-weight:800;letter-spacing:-.08em;opacity:.75}.project-content{padding:38px clamp(24px,4vw,52px)}.meta{display:flex;justify-content:space-between;gap:12px;color:#68756c;font-size:12px}.project h2{font-size:clamp(28px,4vw,42px);line-height:1.08;letter-spacing:-.05em;margin:18px 0 10px}.description,.story p,.facts p{line-height:1.65;color:#53635b;margin:0}.story{padding-top:22px}.story h3,.facts h3{margin:0 0 8px}.facts{display:grid;grid-template-columns:1fr 1.3fr;gap:18px;padding-top:24px;margin-top:24px;border-top:1px solid #e9e9e1}.tags{display:flex;flex-wrap:wrap;gap:8px;margin:22px 0 0}.tags span{background:#eff3ed;border-radius:999px;padding:7px 10px;font-size:12px;color:#41624c}.links{display:flex;flex-wrap:wrap;gap:10px;margin-top:24px}.links a{color:#173f2c;font-weight:700;text-decoration:none;border:1px solid #d6e0d4;border-radius:999px;padding:11px 15px}.links a:hover{background:#e9f1e7}.empty{padding:70px 20px;text-align:center;border:1px dashed #b6c4b4;border-radius:20px}.empty>span{font-size:34px;color:#527264}.empty h2{margin:12px 0 4px}.empty p{color:#53635b}.footer{border-top:1px solid #d9d8cd;padding:24px 0 36px;color:#647169;font-size:12px;display:flex;justify-content:space-between;gap:20px}@media(max-width:700px){.cover{object-position:var(--cover-position-mobile,var(--cover-position,50% 46%))}.wrap{width:min(100% - 28px,560px)}.masthead{padding:20px 0}.intro{padding:58px 0 38px}.project{grid-template-columns:1fr;border-radius:18px}.cover{min-height:220px;height:240px}.project-content{padding:26px 22px}.facts{grid-template-columns:1fr}.projects{gap:18px;padding-bottom:52px}.footer{flex-direction:column}}@media(prefers-reduced-motion:no-preference){.project{animation:rise .45s ease both}.project:nth-child(2){animation-delay:.08s}@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}}@media print{body{background:#fff}.wrap{width:100%}.project{box-shadow:none;break-inside:avoid}.intro{padding:35px 0}.links a{color:#000}}
${themeCss}</style></head><body class="theme-${theme}"><header class="wrap masthead"><span class="brand">folio®</span><span class="local">Портфолио · ${specialization}</span></header><main class="wrap"><section class="intro"><span class="eyebrow">ПОРТФОЛИО · ${specialization.toUpperCase()}</span><h1>${name}</h1><p>${introduction}</p>${contacts ? `<nav class="links profile-links" aria-label="Контакты автора">${contacts}</nav>` : ""}<span class="count">${caseCountLabel(projects.length).toUpperCase()}</span></section><section class="projects" aria-label="Избранные проекты">${projectMarkup || empty}</section></main><footer class="wrap footer"><span>Собрано в folio® · ${new Date().getFullYear()}</span><span>Автономная страница портфолио</span></footer></body></html>`;
}

export function markdownExport(model) {
  const developer = normalizeDeveloper(model.developer);
  const lines = [`# ${model.title || "Портфолио"}`, "", `**${developer.full_name}** · ${developer.specialization}`, ""];
  if (developer.introduction) lines.push(developer.introduction, "");
  const contacts = [developer.include_email && developer.email ? `[Email](mailto:${developer.email})` : null,
    developer.include_website && developer.website_url ? `[Сайт](${developer.website_url})` : null,
    developer.include_github && developer.github_url ? `[GitHub](${developer.github_url})` : null].filter(Boolean);
  if (contacts.length) lines.push(`**Контакты:** ${contacts.join(" · ")}`, "");
  for (const p of [...model.projects].sort((a, b) => Number(b.featured) - Number(a.featured))) {
    lines.push(`## ${p.featured ? "★ " : ""}${p.title}`, "", `*${p.type} · ${p.status} · ${p.created_at}*`, "", p.description, "");
    if (p.role) lines.push(`**Моя роль:** ${p.role}`, "");
    for (const [heading, content] of [["Контекст задачи", p.context], ["Решение", p.solution], ["Этапы процесса", p.process]]) {
      if (content) lines.push(`### ${heading}`, "", content, "");
    }
    if (p.outcome) lines.push(`**Результат:** ${p.outcome}`, "");
    if (p.metrics) lines.push(`**Метрики:** ${p.metrics}`, "");
    if (p.tags?.length) lines.push(`**Теги:** ${p.tags.join(", ")}`, "");
    if (p.technologies.length) lines.push(`**Стек:** ${p.technologies.join(", ")}`, "");
    const links = [p.demo_url && `[Демо](${p.demo_url})`, p.repository_url && `[Репозиторий](${p.repository_url})`].filter(Boolean);
    if (links.length) lines.push(links.join(" · "), "");
  }
  return lines.join("\n").trimEnd() + "\n";
}

export function csvExport(model) {
  const fields = ["id", "sort_order", "type", "title", "description", "context", "role", "solution", "process", "outcome", "metrics", "tags", "featured", "created_at", "status", "technologies", "demo_url", "page_count", "repository_url", "backend_stack"];
  // Prefix spreadsheet formula starters (including full-width variants) with
  // an apostrophe before CSV quoting. This keeps user-controlled cells inert
  // when the file is opened directly in common spreadsheet applications.
  const quote = (value) => {
    const text = String(value ?? "");
    const safe = /^[\s\uFEFF]*[=+\-@＝＋－＠]/u.test(text) ? `'${text}` : text;
    return `"${safe.replaceAll('"', '""')}"`;
  };
  const rows = model.projects.map((p) => [p.id, p.sort_order ?? p.id, p.type, p.title, p.description, p.context, p.role, p.solution, p.process, p.outcome, p.metrics, (p.tags || []).join(", "), p.featured ? "Да" : "", p.created_at, p.status, p.technologies.join(", "), p.demo_url, p.page_count ?? "", p.repository_url ?? "", p.backend_stack ?? ""]);
  return "\uFEFF" + [fields, ...rows].map((row) => row.map(quote).join(";")).join("\r\n");
}

export class IndexedPortfolioStore {
  constructor(name = "folio-workspace", key = "portfolio") { this.name = name; this.key = key; this.dbPromise = null; }
  async open() {
    if (!globalThis.indexedDB) throw new Error("В этом браузере IndexedDB недоступна.");
    if (!this.dbPromise) {
      let shared;
      const opening = new Promise((resolve, reject) => {
        let settled = false;
        let blockedTimer = null;
        const settleError = error => {
          if (settled) return;
          settled = true;
          if (blockedTimer !== null) clearTimeout(blockedTimer);
          reject(error);
        };
        const settleDatabase = db => {
          if (settled) { db.close(); return; }
          settled = true;
          if (blockedTimer !== null) clearTimeout(blockedTimer);
          db.onversionchange = () => {
            db.close();
            if (this.dbPromise === shared) this.dbPromise = null;
          };
          resolve(db);
        };
        const request = indexedDB.open(this.name, 1);
        request.onupgradeneeded = () => {
          if (!request.result.objectStoreNames.contains("records")) {
            request.result.createObjectStore("records", { keyPath: "key" });
          }
        };
        request.onblocked = () => {
          if (blockedTimer !== null) return;
          blockedTimer = setTimeout(() => settleError(new Error(
            "IndexedDB заблокирована другой вкладкой. Закройте старые вкладки приложения и повторите попытку."
          )), 5000);
        };
        request.onsuccess = () => settleDatabase(request.result);
        request.onerror = () => settleError(request.error || new Error("Не удалось открыть IndexedDB."));
      });
      shared = opening.catch(error => {
        if (this.dbPromise === shared) this.dbPromise = null;
        throw error;
      });
      this.dbPromise = shared;
    }
    return this.dbPromise;
  }
  async getRecord() {
    const db = await this.open();
    return new Promise((resolve, reject) => {
      const request = db.transaction("records", "readonly").objectStore("records").get(this.key);
      request.onsuccess = () => {
        const record = request.result;
        resolve({ value: record?.value ?? null, revision: Number.isSafeInteger(record?.revision) && record.revision >= 0 ? record.revision : 0 });
      };
      request.onerror = () => reject(request.error);
    });
  }
  async get() {
    return (await this.getRecord()).value;
  }
  async put(value, { expectedRevision } = {}) {
    const db = await this.open();
    return new Promise((resolve, reject) => {
      const transaction = db.transaction("records", "readwrite");
      const records = transaction.objectStore("records");
      const currentRequest = records.get(this.key);
      let conflict = false;
      let writtenRevision = 0;
      let writeError = null;
      currentRequest.onsuccess = () => {
        const currentRevision = Number.isSafeInteger(currentRequest.result?.revision) && currentRequest.result.revision >= 0 ? currentRequest.result.revision : 0;
        if (expectedRevision !== undefined && currentRevision !== expectedRevision) {
          conflict = true;
          transaction.abort();
          return;
        }
        writtenRevision = currentRevision + 1;
        const writeRequest = records.put({ key: this.key, value, revision: writtenRevision });
        writeRequest.onerror = () => { writeError = writeRequest.error || null; };
      };
      transaction.oncomplete = () => resolve(writtenRevision);
      transaction.onerror = () => reject(writeError || transaction.error || new Error("Не удалось записать данные."));
      transaction.onabort = () => {
        if (conflict) {
          const error = new Error("Портфолио уже изменилось в другой вкладке.");
          error.name = "PortfolioWriteConflictError";
          reject(error);
          return;
        }
        reject(writeError || transaction.error || new Error("Не удалось завершить запись."));
      };
    });
  }
}
