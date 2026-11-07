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
  return h("section", { class: "evidence-group", "aria-label": `Keyword group ${index + 1}` },
    h("div", { class: "group-heading" },
      h("h4", {}, `Keyword group ${index + 1}`),
      h("span", { class: "point-label" }, "Equal credit")),
    h("ul", { class: "alternatives" }, group.alternatives.map(alternativeRow)));
}

export default {
  RubricOutput: (value) => h("div", { class: "rubric-result" },
    h("header", { class: "rubric-header" },
      h("div", {},
        h("p", { class: "eyebrow" }, value.question_id),
        h("h2", {}, "Keyword rubric")),
      h("span", { class: "group-count" }, `${value.rubric.length} keyword groups`)),
    h("p", { class: "scoring-guide" },
      "Score = 1 + 3 × matched groups / total groups. Each group counts once when any option matches. Within an option, every required phrase must appear and every excluded phrase must be absent."),
    h("div", { class: "evidence-list" }, value.rubric.map(evidenceGroup))),
};
