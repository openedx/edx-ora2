import { typesetMath } from 'oa_mathjax';

/*
Tests for MathJax typesetting across MathJax v2 and v3/v4.
*/

describe("OpenAssessment.typesetMath", function() {

    var element = null;
    var originalMathJax = null;

    beforeEach(function() {
        element = document.createElement('div');
        originalMathJax = window.MathJax;
    });

    afterEach(function() {
        if (typeof originalMathJax === 'undefined') {
            delete window.MathJax;
        } else {
            window.MathJax = originalMathJax;
        }
    });

    it("typesets through the v3/v4 API when it is available", function(done) {
        var typesetPromise = jasmine.createSpy('typesetPromise').and.returnValue(Promise.resolve());
        window.MathJax = {
            startup: { promise: Promise.resolve() },
            typesetPromise: typesetPromise
        };

        typesetMath(element).then(function() {
            expect(typesetPromise).toHaveBeenCalledWith([element]);
            done();
        });
    });

    it("typesets through the v2 Hub API when that is all there is", function(done) {
        var queue = jasmine.createSpy('Queue');
        window.MathJax = { Hub: { Queue: queue } };

        typesetMath(element).then(function() {
            expect(queue).toHaveBeenCalledWith(['Typeset', window.MathJax.Hub, element]);
            done();
        });
    });

    // Under MathJax v4 the global is defined but has no `Hub`. Reaching for
    // `MathJax.Hub.Queue` in that case is what used to throw.
    it("does not throw when MathJax is v4-shaped but not ready", function(done) {
        window.MathJax = {};

        typesetMath(element).then(function() {
            done();
        });
    });

    it("does nothing when the runtime provides no MathJax", function(done) {
        delete window.MathJax;

        typesetMath(element).then(function() {
            done();
        });
    });

    it("does nothing when given no element", function(done) {
        var typesetPromise = jasmine.createSpy('typesetPromise').and.returnValue(Promise.resolve());
        window.MathJax = {
            startup: { promise: Promise.resolve() },
            typesetPromise: typesetPromise
        };

        typesetMath(null).then(function() {
            expect(typesetPromise).not.toHaveBeenCalled();
            done();
        });
    });
});
