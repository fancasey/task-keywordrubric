import { h } from "./kit/components.js";

function phrases(items, kind) {
  return h("span", { class: "phrases" }, items.map((phrase) =>
    h("span", { class: `phrase ${kind}` }, phrase)));
}

function alternativeRow(alternative, index) {
  return h("li", { class: "alternative" },
    h("span", { class: "option-label" }, index === 0 ? "MATCH" : "OR"),
    h("div", { class: "conditions" },
      h("div", { class: "condition" },
        h("span", { class: "condition-label" }, "All required"),
        phrases(alternative.all_of, "required")),
      alternative.none_of.length > 0 && h("div", { class: "condition" },
        h("span", { class: "condition-label" }, "None allowed"),
        phrases(alternative.none_of, "excluded"))));
}

function evidenceGroup(group, index) {
  return h("section", { class: "evidence-group", "aria-label": `Evidence group ${index + 1}` },
    h("div", { class: "group-heading" },
      h("h4", {}, `Evidence ${index + 1}`),
      h("span", { class: "point-label" }, "+1 point")),
    h("ul", { class: "alternatives" }, group.alternatives.map(alternativeRow)));
}

function dimensionSection(dimension, index) {
  return h("details", { class: "dimension", open: index === 0 },
    h("summary", { class: "dimension-heading" },
      h("span", { class: "dimension-title" }, dimension.dimension_id),
      h("span", { class: "dimension-meta" }, `${dimension.evidence.length} evidence groups · Score 1–4`)),
    h("div", { class: "evidence-list" }, dimension.evidence.map(evidenceGroup)));
}

export default {
  RubricOutput: (value) => h("div", { class: "rubric-result" },
    h("header", { class: "rubric-header" },
      h("div", {},
        h("p", { class: "eyebrow" }, value.question_id),
        h("h2", {}, "Keyword rubric")),
      h("span", { class: "dimension-count" }, `${value.rubric.length} dimensions`)),
    h("p", { class: "scoring-guide" },
      "Start at 1 point per dimension. Each evidence group adds 1 point when any option matches. Within an option, every required phrase must appear and every excluded phrase must be absent."),
    h("div", { class: "dimensions" }, value.rubric.map(dimensionSection))),
};
