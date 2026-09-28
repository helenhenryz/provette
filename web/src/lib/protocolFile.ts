/* Every protocol the robot runs defines run(protocol); a .py without one is some other Python
   file. The API refuses it too (api/checks.py `protocol_problem`, the same pattern). */
const RUN = /^[ \t]*(?:async[ \t]+)?def[ \t]+run[ \t]*\(/m;
export function looksLikeProtocol(text: string): boolean {
  return !text.includes("\u0000") && RUN.test(text);
}
