/**
Container that handles addition / deletion of arbitrary items.

An item is any object that has a `getFieldValues()` method,
which should return a JSON-serializable representation
of the item.

Containers copy "template" elements to create new items.
For example, to create a container for an item called "test_item",
the DOM should look something like:
    <div id="test_container" />
    <div id="test_item_template">
        <div class="test_item_remove_button">Remove</div>
        <p>This is the default value for the item.</p>
    </div>
    <div id="test_item_add_button">Add</div>

You can then initialize the container:
>>> var container = $("#test_container").get(0);
>>> var template = $("#test_item_template").get(0);
>>> var addButton = $("#test_item_add_button").get(0);
>>>
>>> container = OpenAssessment.Container(
>>>     ContainerItem, {
>>>         containerElement: container,
>>>         templateElement: template,
>>>         addButtonElement: addButton,
>>>         removeButtonClass: "test_item_remove_button"
>>>         containerItemClass: "test_item"
>>>     }
>>> );

The container is responsible for initializing the "add" and "remove" buttons,
including for pre-existing items in the container element.

Templates elements are never deleted, so they should be hidden using CSS styles.

Args:
    containerItem (object): The container item object used to access
        the contents of items in the container.

Kwargs:
    containerElement (DOM element): The element representing the container.
    templateElement (DOM element):  The element containing the template for creating new items.
    addButtonElement (DOM element): The element of the button used to add new items to the container.
    removeButtonClass (string): The CSS class of the button that removes an item from the container.
        There may be one of these for each item in the container.
    containerItemClass (string): The CSS class of items in the container.
        New items will be assigned this class.

**/
OpenAssessment.Container = function(containerItem, kwargs) {
    this.containerItem = containerItem;
    this.containerElement = kwargs.containerElement;
    this.templateElement = kwargs.templateElement;
    this.addButtonElement = kwargs.addButtonElement;
    this.removeButtonClass = kwargs.removeButtonClass;
    this.containerItemClass = kwargs.containerItemClass;

    // Install a click handler for the add button
    $(this.addButtonElement).click($.proxy(this.add, this));

    // Find items already in the container and install click
    // handlers for the delete buttons.
    var container = this;
    $("." + this.removeButtonClass, this.containerElement).click(
        function(eventData) { container.remove(eventData.target); }
    );

    // Initialize existing items, in case they need to install their
    // own event handlers.
    $("." + this.containerItemClass, this.containerElement).each(
        function(index, element) { new container.containerItem(element); }
    );
};

OpenAssessment.Container.prototype = {
    /**
    Adds a new item to the container.
    **/
    add: function() {
        // Copy the template into the container
        // Remove any CSS IDs (since now the element is not unique)
        // and add the item class so we can find it later.
        $(this.templateElement)
            .clone()
            .removeAttr('id')
            .toggleClass('is--hidden', false)
            .toggleClass(this.containerItemClass, true)
            .appendTo($(this.containerElement));

        // Install a click handler for the delete button
        // Since we just added the new element to the container,
        // it should be the last one.
        var container = this;
        var containerItem = $("." + this.containerItemClass, this.containerElement).last();
        containerItem.find('.' + this.removeButtonClass)
            .click(function(eventData) { container.remove(eventData.target); } );

        // Initialize the item, allowing it to install event handlers.
        new this.containerItem(containerItem.get(0));
    },

    /**
    Remove the item associated with an element.
    If the element is not itself an item, traverse up the
    DOM tree until an item is found.

    Args:
        element (DOM element): An element representing the container item
            or an element within the container item.

    **/
    remove: function(element) {
        $(element).closest("." + this.containerItemClass).remove();
    },

    /**
    Retrieves the values that each container defines for itself, in the order in which they are
    presented in the DOM.

    Returns:
        array: The values representing each container item.

    **/
    getItemValues: function () {
        var values = [];
        var container = this;

        $("." + this.containerItemClass, this.containerElement).each(
            function(index, element) {
                var containerItem = new container.containerItem(element);
                var fieldValues = containerItem.getFieldValues();
                values.push(fieldValues);
            }
        );

        return values;
    },

    /**
    Retrieve the element representing an item in this container.

    Args:
        index (int): The index of the item, starting from 0.

    Returns:
        DOM element if the item is found, otherwise null.

    **/
    getItemElement: function(index) {
        var element = $("." + this.containerItemClass, this.containerElement).get(index);
        return (element !== undefined) ? element : null;
    },
};
