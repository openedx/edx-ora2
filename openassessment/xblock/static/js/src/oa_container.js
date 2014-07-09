/**
 * Created by gward on 7/9/14.
 */

/**
Container to store arbitrary DOM elements for insertion, deletion and installation of self-delete buttons

Args:
    element (DOM element): The DOM element representing the container (usually an OL or a UL)
    selectorDictionary (dict): Has keys which map selector (str) to Container Item classes to which they are related

Returns:
    OpenAssessment.Container
**/
OpenAssessment.Container = function(element, selectorDictionary){
    this.element = element;
    this.selectorDictionary = selectorDictionary;
    this.installDeleteButtons(element);
};

OpenAssessment.Container.prototype = {
    /**
    Adds a new item of the specified type to the DOM.
    If the type is unrecognized,

    Throws:
        An error that alerts the user that an unknown type was attempted to be added to the container.
    **/
    add: function(selectorString){
        var type = this.selectorDictionary[selectorString];
        if (type == undefined){
            throw 'The string: ('+ selectorString + ') is not known by this container.';
        }
        this.element.append(this.getHtmlTemplate(selectorString));
    },

    /**
    Removes a specified item from the DOM. This is distinct from (and not used by) delete buttons.

    Args:
        index(int): The index of the specified item to remove.

    **/
    remove: function(index){
        var count = 0;
        $(this.element).children().each(function(){
            if (count == index){
                $(this).remove();
                return;
            }
            count++;
        });
    },

    /**
    Installs delete buttons on all sections of a certain element.
    Called both when we create a container, and when we add new elements.

    Args:
        liveElement (Jquery Element): an element that allows us to define the scope of delete button creation.
    **/
    installDeleteButtons: function(liveElement){
        $('.openassessment_delete_button', liveElement).each(function() {
            $(this).click(function () {
                liveElement.closest('.openassessment_deletable').remove();
            });
        });
    },

    /**
    Gets the values that each container defines for itself, in the order in which they are
    presented in the DOM.

    Returns:
        (list of ...): The list of the values that each container item associates with itself.

    Throws:
        An exception which notifies the user if there is an element in their container that is not
        recognized as a part of the containers definition.
    **/
    getItemValues: function () {
        var values = [];
        var container = this;
        $(this.element).children().each(function(){

            //Attempts to find the type of a given element
            var classes = $(this).getClasses();
            var type = undefined;
            for(var i = 0; i < classes.length; i++){
                var c = classes[i];
                if (container.selectorDictionary[c] != undefined){
                    type = container.selectorDictionary[c];
                }
            }
            // If we couldn't resolve the type, we throw an exception.
            if (type == undefined){
                throw 'An item with classes (' + classes.join(' ') +
                    ') was not found in a dict of known container items.';
            }

            var item = new type($(this));
            var value = item.getFieldValues();
            values.push(value);
        });
        return values;
    },

    /**
    Returns the specific HTML template that is defined for its container items.

    Returns:
        (str): The HTML template associated with the container item's type.
    **/
    getHtmlTemplate: function(selectorString){
        var element = $('.' + selectorString + '.openassessment_template', this.element);
        return element.html();
    }
};

