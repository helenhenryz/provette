/* The frozen files the rendering tests draw on, saved under tests/web/fixtures/ (refresh them
   with `make web-fixtures`): the API's own answers for one episode of the evaluation, and
   `series`, the analysis of the committed test protocol tests/fixtures/protocols/dil_series.py,
   which the replay's tests draw so they do not move when the evaluation is run again. */

import analysisJson from "../../../tests/web/fixtures/analysis-dil-03.json";
import episodeJson from "../../../tests/web/fixtures/episode-dil-03.json";
import episodesJson from "../../../tests/web/fixtures/episodes.json";
import rulesJson from "../../../tests/web/fixtures/rules.json";
import seriesJson from "../../../tests/web/fixtures/analysis-dil-series.json";
import type { Analysis, EpisodeDetail, EpisodeList, RuleRow } from "../lib/api";

export const analysis = analysisJson as unknown as Analysis;
export const series = seriesJson as unknown as Analysis;
export const episode = episodeJson as unknown as EpisodeDetail;
export const episodes = episodesJson as unknown as EpisodeList;
export const rules = (rulesJson as { rules: RuleRow[] }).rules;
