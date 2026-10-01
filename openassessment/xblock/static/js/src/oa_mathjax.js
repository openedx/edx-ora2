/**
 * MathJax typesetting that works against both MathJax v2 and v3/v4.
 *
 * The host platform loads and configures MathJax, not this XBlock, so which
 * major version is available is out of our control. v2 exposes the queue-based
 * `MathJax.Hub` API; v3 removed `Hub` in favour of `MathJax.typesetPromise`.
 * Both are supported here so ORA renders math on either.
 */

/**
 * Typeset math inside an element, if the runtime provides MathJax.
 *
 * Safe to call when MathJax is absent, which is the case in the workbench and
 * in tests.
 *
 * @param {Element} element - the DOM element to typeset.
 * @returns {Promise} resolves once typesetting is done. Resolves immediately
 *   when MathJax is missing, and when only the v2 API is available, since that
 *   API is queue-based and reports completion through callbacks instead.
 */
export const typesetMath = (element) => {
  if (typeof MathJax === 'undefined' || MathJax === null || !element) {
    return Promise.resolve();
  }

  if (MathJax.startup && MathJax.startup.promise && typeof MathJax.typesetPromise === 'function') {
    return MathJax.startup.promise.then(() => MathJax.typesetPromise([element]));
  }

  if (MathJax.Hub && typeof MathJax.Hub.Queue === 'function') {
    MathJax.Hub.Queue(['Typeset', MathJax.Hub, element]);
  }

  return Promise.resolve();
};

export default typesetMath;
