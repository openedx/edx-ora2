/**
 * Created by gward on 7/9/14.
 */

/**
Container to store arbitrary DOM elements for insertion, deletion and removal.
ASSUMPTIONS:  All containerItems have the same class name

Args:
    element (DOM element): The DOM element representing the container (usually an OL or a UL)
    htmlDefinition (dict): Has the following keys:
        'class' (str): The class name (will be used for selection of all sub-elements)
        'template' (str): The String representing the original HTML definition for the item
        'replace' (str) OPTIONAL: The string sequence in the html to replace with the id/identifier
    type (ContainerItem): The class of item that the container will hold.

Returns:
    OpenAssessment.Container
**/
OpenAssessment.Container = function(element, htmlDefinition, type){
    this.element = element;
    this.htmlDefinition = htmlDefinition;
    this.type = type;

    this.id = 0;

    this.items = [];
    this.itemSelectors = [];
};

OpenAssessment.Container.prototype = {
    /**
    Adds a new item to the DOM and to internal tracking mechanisms.

    Returns:
        (str): The selector for the new item.
    **/
    add: function(){
        var newItem = this.type(this);
        var selector = newItem.getSelector();
        this.items.push(newItem);
        this.itemSelectors.push(selector);
        this.element.append(newItem.getHtml());
        return selector;
    },

    /**
    Removes a specified item from the DOM and from internal tracking mechanisms.

    Args:
        index(int): The index of the specified item to remove.

    **/
    remove: function(index){
        $(this.itemSelectors[index], this.element).remove();
        this.items = this.items.splice(index, 1);
        this.itemSelectors = this.itemSelectors.splice(index, 1);
    },

    /**
    Gets the values that each container defines for itself, in the order in which they are
    presented in the DOM.

    Returns:
        (list of ...): The list of the values that each container item associates with itself.
    **/
    getItemValues: function () {
        var values = [];
        var container = this;
        $('.' + this.htmlDefinition.class, this.element).each(function(){
            var index = container.itemSelectors.indexOf($(this).id);
            values.push(container.items[index].getFieldValues());
        });
        return values;
    },

    /**
    Returns the specific HTML template that is defined for its container items.

    Returns:
        (str): The HTML template associated with the container item's type.
    **/
    getHtmlDefinition: function(){
        return this.htmlDefinition;
    },

    /**
    Returns a new ID every time it is called. This is a method relied on by some but not all Container Items.

    Returns:
        (int): An ID to associate with a new item. [1-inf)
    **/

    generateItemID: function(){
        this.id += 1;
        return this.id;
    }
};

