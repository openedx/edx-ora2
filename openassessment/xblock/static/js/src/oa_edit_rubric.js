/**
Interface for editing rubric definitions.
**/
OpenAssessment.EditRubricView = function(element) {
    this.element = element;
};

OpenAssessment.EditRubricView.prototype = {

    /**
    Install event handlers.
    **/
    load: function() {
        //this.container = new Container(this.element, "openassessment__rubric__criterion", OpenAssessment.RubricCriterion);
    },

    /**
    [
        {
            order_num: 0,
            name: 'Criteria!'
            prompt: 'prompt',
            feedback: 'disabled',
            options: [
                {
                    order_num: 0,
                    name: 'name',
                    explanation: 'explanation',
                    points: 1
                },
                ...
            ]
        },
        ...
    ]
    **/
    criteriaDefinition: function() {
        //return this.container.getItemValues();
    },
};