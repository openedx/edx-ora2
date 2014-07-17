

var generateOptionString = function(name, points){
    return gettext(name + ' - ' + points + ' points')
};

OpenAssessment.RubricValidationEventHandler = function () {
    this.element = $('#oa_student_training_editor');
    this.alert = new OpenAssessment.ValidationAlert($('#openassessment_rubric_validation_alert', this.element));
};

OpenAssessment.RubricValidationEventHandler.prototype = {

    optionRefresh: function(criterionName, oldName, newName, newPoints){
        $('.openassessment_training_example_criterion', this.element).each(function(){
            if ($(this).data('criterion') == criterionName && $(this).val() == oldName) {
                $(this).val(newName);
                $(this).text(generateOptionString(newName, newPoints));
            }
        });
    },

    optionAdd: function(criterionName){
        $('.openassessment_training_example_criterion_option', this.element).each(function(){
            if ($(this).data('criterion') == criterionName) {
                $(this).append(
                    "<option value=''> </option>"
                );
            }
        });
    },

    optionRemove: function(criterionName, optionName){
        var removed = 0;
        $('.openassessment_training_example_criterion_option', this.element).each(function(){
            if ($(this).data('criterion') == criterionName && $(this).val() == optionName) {
                $(this).val("");
                $(this).addClass("openassessment_highlighted_field");
                removed++;
            }
        });
        if (removed > 0){
            var title = "Option Deletion Led to Invalidation";
            var msg = "Because you deleted an option, there were " + removed + " instance(s) of training examples" +
                "where the choice had to be reset.";
            this.alert.setMessage(title, msg);
        }
    },

    criterionRename: function(criterionName, newValue){
        $('.openassessment_training_example_criterion', this.element).each(function(){
            if ($(this).data('criterion') == criterionName){
                $(".openassessment_training_example_criterion_name_wrapper", this).text(newValue);
            }
        });
    },

    criterionAdd: function() {
        $(".openassessment_training_example_criterion", this.element).each(function(){
            $(this).append(
                '<li class="field comp-setting-entry openassessment_training_example_criterion" data-criterion=APPLES>' +
                    '<div class="wrapper-comp-setting">' +
                        '<label class="openassessment_training_example_criterion_name setting-label">' +
                            '<div class="openassessment_training_example_criterion_name_wrapper">' +
                                'Banannas!' +
                            '</div>' +
                            '<select class="openassessment_training_example_criterion_option setting-input" data-criterion=APPLES>' +
                            '</select>' +
                        '</label>'+
                    '</div>'+
                '</li>'
            );



        });
    }

};
