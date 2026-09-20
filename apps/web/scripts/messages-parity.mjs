import { parse, TYPE } from "@formatjs/icu-messageformat-parser";

/**
 * Catalogue parity rules (FE-051). English is the source of truth. Every other locale must have
 * exactly the same keys and nesting, valid ICU syntax, the same variables with the same types, and
 * the same `select` branches. A leaf is a non-empty string, or `null` while a translation is pending.
 * Status is checked against content: a domain is only `reviewed` or `machine_assisted` when it has
 * no gaps, and only with a named reviewer and date.
 */

export const LOCALES = ["en", "ha", "ig", "yo"];
const STATUSES = new Set(["reviewed", "machine_assisted", "pending"]);
const PLURAL_CATEGORIES = new Set(["zero", "one", "two", "few", "many", "other"]);
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

const isObject = (value) => typeof value === "object" && value !== null && !Array.isArray(value);

/** Every leaf as [path, value]; a non-object, non-string, non-null leaf is reported by the caller. */
export function leaves(node, prefix = []) {
  if (!isObject(node)) {
    return [[prefix.join("."), node]];
  }

  return Object.entries(node).flatMap(([key, value]) => leaves(value, [...prefix, key]));
}

/** Variable name to its ICU type, plus the `select` branches and `plural` `other` presence found. */
export function describeMessage(source) {
  const ast = parse(source, { requiresOtherClause: false });
  const variables = new Map();
  const selects = new Map();
  const problems = [];

  const record = (name, type) => {
    const previous = variables.get(name);

    if (previous !== undefined && previous !== type) {
      problems.push(`variable "${name}" is used as both ${previous} and ${type}`);
    }
    variables.set(name, type);
  };

  const walk = (elements) => {
    for (const element of elements) {
      switch (element.type) {
        case TYPE.argument:
          record(element.value, "argument");
          break;
        case TYPE.number:
          record(element.value, "number");
          break;
        case TYPE.date:
          record(element.value, "date");
          break;
        case TYPE.time:
          record(element.value, "time");
          break;
        case TYPE.tag:
          record(element.value, "tag");
          walk(element.children);
          break;
        case TYPE.select: {
          record(element.value, "select");
          selects.set(element.value, Object.keys(element.options).toSorted());
          if (!("other" in element.options)) {
            problems.push(`select "${element.value}" has no "other" branch`);
          }
          for (const option of Object.values(element.options)) {
            walk(option.value);
          }
          break;
        }
        case TYPE.plural: {
          record(element.value, "plural");
          const names = Object.keys(element.options);
          if (!names.includes("other")) {
            problems.push(`plural "${element.value}" has no "other" branch`);
          }
          for (const name of names) {
            if (!PLURAL_CATEGORIES.has(name) && !/^=\d+$/.test(name)) {
              problems.push(`plural "${element.value}" has unknown branch "${name}"`);
            }
          }
          for (const option of Object.values(element.options)) {
            walk(option.value);
          }
          break;
        }
        default:
          break;
      }
    }
  };

  walk(ast);

  return { variables, selects, problems };
}

function compareShape(source, target, path, errors, locale) {
  const sourceKeys = isObject(source) ? Object.keys(source) : undefined;
  const targetKeys = isObject(target) ? Object.keys(target) : undefined;

  if (sourceKeys === undefined || targetKeys === undefined) {
    if ((sourceKeys === undefined) !== (targetKeys === undefined)) {
      errors.push(
        `${locale}: "${path}" is ${sourceKeys ? "an object" : "a leaf"} in en but not here`
      );
    }
    return;
  }

  for (const key of sourceKeys) {
    const next = path === "" ? key : `${path}.${key}`;

    if (!(key in target)) {
      errors.push(`${locale}: missing key "${next}"`);
    } else {
      compareShape(source[key], target[key], next, errors, locale);
    }
  }

  for (const key of targetKeys) {
    if (!(key in source)) {
      errors.push(`${locale}: extra key "${path === "" ? key : `${path}.${key}`}" not in en`);
    }
  }
}

function checkMessage(path, source, translated, locale, errors) {
  let sourceInfo;

  try {
    sourceInfo = describeMessage(source);
  } catch (error) {
    errors.push(
      `en: "${path}" is not valid ICU (${error instanceof Error ? error.message : "parse error"})`
    );
    return;
  }

  for (const problem of sourceInfo.problems) {
    errors.push(`en: "${path}": ${problem}`);
  }

  if (translated === null || translated === undefined) {
    return;
  }

  let info;

  try {
    info = describeMessage(translated);
  } catch (error) {
    errors.push(
      `${locale}: "${path}" is not valid ICU (${error instanceof Error ? error.message : "parse error"})`
    );
    return;
  }

  for (const problem of info.problems) {
    errors.push(`${locale}: "${path}": ${problem}`);
  }

  for (const [name, type] of sourceInfo.variables) {
    const found = info.variables.get(name);

    if (found === undefined) {
      errors.push(`${locale}: "${path}" is missing variable "${name}"`);
    } else if (found !== type) {
      errors.push(`${locale}: "${path}" uses "${name}" as ${found}, en uses ${type}`);
    }
  }

  for (const name of info.variables.keys()) {
    if (!sourceInfo.variables.has(name)) {
      errors.push(`${locale}: "${path}" has variable "${name}" that en does not`);
    }
  }

  for (const [name, branches] of sourceInfo.selects) {
    const found = info.selects.get(name);

    if (found !== undefined && found.join("|") !== branches.join("|")) {
      errors.push(
        `${locale}: "${path}" select "${name}" has branches [${found}], en has [${branches}]`
      );
    }
  }
}

/**
 * @param {{ catalogues: Record<string, unknown>, status: any }} input
 * @returns {string[]} human-readable errors; empty means the catalogues are consistent
 */
export function checkCatalogues({ catalogues, status }) {
  const errors = [];
  const en = catalogues["en"];

  for (const locale of LOCALES) {
    if (!isObject(catalogues[locale])) {
      errors.push(`${locale}: catalogue is missing or not an object`);
    }
  }

  if (errors.length > 0) {
    return errors;
  }

  const sourceLeaves = new Map(leaves(en));

  for (const [path, value] of sourceLeaves) {
    if (typeof value !== "string" || value.trim() === "") {
      errors.push(`en: "${path}" must be a non-empty string`);
    }
  }

  for (const locale of LOCALES.filter((code) => code !== "en")) {
    compareShape(en, catalogues[locale], "", errors, locale);

    for (const [path, value] of leaves(catalogues[locale])) {
      if (value !== null && (typeof value !== "string" || value.trim() === "")) {
        errors.push(`${locale}: "${path}" must be a non-empty string or null (pending)`);
      }
    }
  }

  for (const [path, value] of sourceLeaves) {
    if (typeof value !== "string") {
      continue;
    }
    for (const locale of LOCALES.filter((code) => code !== "en")) {
      const translated = new Map(leaves(catalogues[locale])).get(path);
      checkMessage(path, value, translated, locale, errors);
    }
  }

  // English is also validated on its own, so a syntax error is caught even with no translations.
  for (const [path, value] of sourceLeaves) {
    if (typeof value === "string") {
      checkMessage(path, value, undefined, "en", errors);
    }
  }

  checkStatus({ catalogues, status, errors });

  return [...new Set(errors)];
}

function checkStatus({ catalogues, status, errors }) {
  const domains = Object.keys(catalogues["en"]);

  if (!isObject(status?.domains) || !isObject(status?.locales)) {
    errors.push("status: must have `domains` and `locales` objects");
    return;
  }

  if (Object.keys(status.domains).toSorted().join("|") !== domains.toSorted().join("|")) {
    errors.push(
      `status: domains [${Object.keys(status.domains)}] must equal catalogue domains [${domains}]`
    );
  }

  for (const [domain, meta] of Object.entries(status.domains)) {
    if (typeof meta?.critical !== "boolean") {
      errors.push(`status: domain "${domain}" needs a boolean "critical"`);
    }
  }

  for (const locale of LOCALES) {
    const entry = status.locales[locale];

    if (!isObject(entry)) {
      errors.push(`status: locale "${locale}" is missing`);
      continue;
    }

    for (const domain of domains) {
      const record = entry[domain];

      if (!isObject(record) || !STATUSES.has(record.status)) {
        errors.push(
          `status: ${locale}.${domain} needs a status of reviewed, machine_assisted, or pending`
        );
        continue;
      }

      const domainLeaves = leaves(catalogues[locale][domain] ?? {}, [domain]);
      const gaps = domainLeaves.filter(([, value]) => value === null).length;

      if (record.status === "pending" && gaps !== domainLeaves.length) {
        errors.push(
          `status: ${locale}.${domain} is pending but has translated text; set a status and reviewer`
        );
      }

      if (record.status !== "pending") {
        if (gaps > 0) {
          errors.push(
            `status: ${locale}.${domain} is ${record.status} but ${gaps} key(s) are still null`
          );
        }
        if (typeof record.reviewer !== "string" || record.reviewer.trim() === "") {
          errors.push(`status: ${locale}.${domain} is ${record.status} and needs a named reviewer`);
        }
        if (typeof record.reviewedOn !== "string" || !ISO_DATE.test(record.reviewedOn)) {
          errors.push(
            `status: ${locale}.${domain} is ${record.status} and needs a reviewedOn date (YYYY-MM-DD)`
          );
        }
      }
    }
  }

  for (const domain of domains) {
    if (status.locales["en"]?.[domain]?.status !== "reviewed") {
      errors.push(`status: en.${domain} is the source and must be reviewed`);
    }
  }
}
