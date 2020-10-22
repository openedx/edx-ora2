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
        <div class="test_item">
            <div class="test_item_remove_button">Remove</div>
            <p>This is the default value for the item.</p>
        </div>
    </div>
    <div id="test_item_add_button">Add</div>

A critical property of this setup is that the element you want to
include/duplicate is wrapped inside of a template element which is
the one that your reference when referring to a template. In the
above example, $("#test_item_template") would be the appropriate
reference to the template.

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
    containerItem (constructor): The constructor of the container item object
        used to access the contents of items in the container.

Kwargs:
    containerElement (DOM element): The element representing the container.
    templateElement (DOM element):  The element containing the template for creating new items.
    addButtonElement (DOM element): The element of the button used to add new items to the container.
    removeButtonClass (string): The CSS class of the button that removes an item from the container.
        There may be one of these for each item in the container.
    containerItemClass (string): The CSS class of items in the container.
        New items will be assigned this class.
    notifier (OpenAssessment.Notifier): Used to send notifications of updates to container items.

* */
export class Container {
  constructor(ContainerItem, kwargs) {
    this.containerElement = kwargs.containerElement;
    this.templateElement = kwargs.templateElement;
    this.addButtonElement = kwargs.addButtonElement;
    this.removeButtonClass = kwargs.removeButtonClass;
    this.containerItemClass = kwargs.containerItemClass;
    this.notifier = kwargs.notifier;
    this.addRemoveEnabled = (typeof kwargs.addRemoveEnabled === 'undefined') || kwargs.addRemoveEnabled;

    // Since every container item should be instantiated with
    // the notifier we were given, create a helper method
    // that does this automatically.
    const container = this;
    this.createContainerItem = function (element) {
      return new ContainerItem(element, container.notifier);
    };
  }

  /**
     Adds event listeners to the container and its children. Must be
     called explicitly when the container is initially created.
     */
  addEventListeners() {
    const container = this;

    if (this.addRemoveEnabled) {
      // Install a click handler for the add button
      $(this.addButtonElement).click($.proxy(this.add, this));

      // Find items already in the container and install click
      // handlers for the delete buttons.
      $(`.${this.removeButtonClass}`, this.containerElement).click(
        (eventData) => {
          const item = container.createContainerItem(eventData.target);
          container.remove(item);
        },
      );
    } else {
      $(this.addButtonElement).addClass('is--disabled');
      $(`.${this.removeButtonClass}`, this.containerElement).addClass('is--disabled');
    }

    // Initialize existing items, in case they need to install their
    // own event handlers.
    $(`.${this.containerItemClass}`, this.containerElement).each(
      (index, element) => {
        const item = container.createContainerItem(element);
        item.addEventListeners();
      },
    );
  }

  /**
    Adds a new item to the container.
    * */
  add() {
    // Copy the template into the container
    // Remove any CSS IDs (since now the element is not unique)
    // and add the item class so we can find it later.
    // Note that the element we add is the first child of the template element.
    // For more on the template structure expected, see the class comment
    $(this.templateElement)
      .children().first()
      .clone()
      .removeAttr('id')
      .toggleClass('is--hidden', false)
      .toggleClass(this.containerItemClass, true)
      .appendTo($(this.containerElement));

    // Since we just added the new element to the container,
    // it should be the last one.
    const container = this;
    const containerItem = $(`.${this.containerItemClass}`, this.containerElement).last();

    // Install a click handler for the delete button
    if (this.addRemoveEnabled) {
      containerItem.find(`.${this.removeButtonClass}`)
        .click((eventData) => {
          const containerItemToRemove = container.createContainerItem(eventData.target);
          container.remove(containerItemToRemove);
        });
    } else {
      containerItem.find(`.${this.removeButtonClass}`).addClass('is--disabled');
    }

    // Initialize the item, allowing it to install event handlers.
    // Fire event handler for adding a new element
    const handlerItem = container.createContainerItem(containerItem);
    handlerItem.addEventListeners();
    handlerItem.addHandler();
  }

  /**
    Remove the item associated with an element.
    If the element is not itself an item, traverse up the
    DOM tree until an item is found.

    Args:
        item: The container item object to remove.

    * */
  remove(item) {
    const itemElement = $(item.element).closest(`.${this.containerItemClass}`);
    const containerItem = this.createContainerItem(itemElement);
    containerItem.removeHandler();
    itemElement.remove();
  }

  /**
    Retrieves the values that each container defines for itself, in the order in which they are
    presented in the DOM.

    Returns:
        array: The values representing each container item.

    * */
  getItemValues() {
    const values = [];
    const container = this;

    $(`.${this.containerItemClass}`, this.containerElement).each(
      (index, element) => {
        const containerItem = container.createContainerItem(element);
        const fieldValues = containerItem.getFieldValues();
        values.push(fieldValues);
      },
    );

    return values;
  }

  /**
    Retrieve the element representing an item in this container.

    Args:
        index (int): The index of the item, starting from 0.

    Returns:
        Container item object or null.

    * */
  getItem(index) {
    const element = $(`.${this.containerItemClass}`, this.containerElement).get(index);
    return (element !== undefined) ? this.createContainerItem(element) : null;
  }

  /**
    Retrieve all elements representing items in this container.

    Returns:
        array of container item objects

    * */
  getAllItems() {
    const container = this;
    return $(`.${this.containerItemClass}`, this.containerElement)
      .map(function () { return container.createContainerItem(this); });
  }
}

export default Container;
