/**
Tests for OA dateutil factory.
**/

describe('OpenAssessment.DateTimeFactory', function() {

    beforeEach(function() {
        // Load the DOM fixture
        loadFixtures('oa_response_date.html');

    });
    describe('apply', function() {
        it('has the correct HTML elements', function() {
            var timeElement = $('.step__title').get(0);
            var datetimeFactory = new OpenAssessment.DateTimeFactory(timeElement);
            datetimeFactory.apply();
            $('.ora-datetime', timeElement).each(function() {
                var self = this;
                expect($(self).data('datetime')).toBe('2020-01-01T00:00:00+00:00');
                expect($(self).data('string')).toContain('due {date}');
            });
        });
    });

    describe('determineContext', function() {
        it('generates a context dict', function() {
            var timeElement = $('.step__title').get(0);
            var datetimeFactory = new OpenAssessment.DateTimeFactory(timeElement);

            $('.ora-datetime', timeElement).each(function() {
                var self = this;
                $(self).attr('data-language', 'en');
                $(self).attr('data-timezone', 'America/Los_Angeles');
            });

            $('.ora-datetime', timeElement).each(function() {
                var el = this;
                var testContext = datetimeFactory.determineContext($(el));
                expect(testContext['datetime']).toBe('2020-01-01T00:00:00+00:00');
                expect(testContext['timezone']).toBe('America/Los_Angeles');
                expect(testContext['language']).toBe('en');
                expect(testContext['format']).toBe('');
            })
        })
    });

    describe('determineDateToken', function() {
        it('defaults', function() {
            var timeElement = $('.step__title').get(0);
            var datetimeFactory = new OpenAssessment.DateTimeFactory(timeElement);

            $('.ora-datetime', timeElement).each(function() {
                var el = this;
                var testDateToken = datetimeFactory.determineDateToken($(el));
                expect(testDateToken).toBe('date');
            });
            $('.ora-datetime', timeElement).each(function() {
                var self = this;
                $(self).attr('data-datetoken', 'TEST');
            });
            $('.ora-datetime', timeElement).each(function() {
                var el = this;
                var testDateToken = datetimeFactory.determineDateToken($(el));
                expect(testDateToken).toBe('TEST');
            })
        })
    });

    describe('isValid', function() {
        it('checks a valid variable', function() {
            var timeElement = $('.step__title').get(0);
            var datetimeFactory = new OpenAssessment.DateTimeFactory(timeElement);
            var testDict = {
                'Invalid date': false,
                'invalid date': true,
                '': false,
                1: true
            };
            Object.keys(testDict).forEach(function(key) {
                expect(datetimeFactory.isValid(key)).toEqual(testDict[key]);
            });
        })
    });
});
