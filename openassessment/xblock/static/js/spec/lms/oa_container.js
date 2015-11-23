/**
 Tests for the Openassessment Container Object.
 **/

describe("OpenAssessment.Container", function() {

    var counter = 0;
    var StubContainerItem = function(element) {
        this.element = element;

        // Assign an ID to the item if it doesn't already have one.
        if ($(element).attr("test_id") === "") {
            $(element).attr("test_id", counter);
            counter += 1;
        }

        this.getFieldValues = function() {
            var testIdNum = parseInt($(element).attr("test_id"), 10);
            return { id: testIdNum };
        };

        this.addHandler = function() {};
        this.removeHandler = function() {};
        this.updateHandler = function() {};
        this.addEventListeners = function() {};
    };

    var container = null;
    var createContainer = function() {
        return new OpenAssessment.Container(
            StubContainerItem, {
                containerElement: $("#container").get(0),
                templateElement: $("#template").get(0),
                addButtonElement: $("#add_button").get(0),
                removeButtonClass: "remove_button",
                containerItemClass: "container_item",
            }
        );
    };

    beforeEach(function() {
        // Reset the counter before each test
        counter = 0;

        // Install a minimal fixture
        // We don't need to use a full ORA2 template for this,
        // so we just define the fixture inline.
        setFixtures(
            '<div id="container" />' +
            '<div id="template">' +
                '<div class="container_item" test_id="">' +
                    '<div class="remove_button" />' +
                '</div>' +
            '</div>' +
            '<div id="add_button" />'
        );

        // Create the container and configure it
        // to use the stub container item.
        container = createContainer();

        // Explicitly add event listeners.
        container.addEventListeners();
    });

    it("adds and removes items", function() {
        // Initially, there should be no items
        expect(container.getItemValues()).toEqual([]);

        // Add an item
        container.add();
        expect(container.getItemValues()).toEqual([
            { id: 0 }
        ]);

        // Add a second item
        container.add();
        expect(container.getItemValues()).toEqual([
            { id: 0 },
            { id: 1 }
        ]);

        // Add a third item
        container.add();
        expect(container.getItemValues()).toEqual([
            { id: 0 },
            { id: 1 },
            { id: 2 }
        ]);

        // Remove the second item
        container.remove(container.getItem(1));
        expect(container.getItemValues()).toEqual([
            { id: 0 },
            { id: 2 },
        ]);

        // Remove the first item
        container.remove(container.getItem(0));
        expect(container.getItemValues()).toEqual([
            { id: 2 },
        ]);

        // Remove the last item
        container.remove(container.getItem(0));
        expect(container.getItemValues()).toEqual([]);
    });

    it("ignores unrecognized DOM elements", function() {
        // Add some items to the container
        container.add();
        container.add();
        expect(container.getItemValues().length).toEqual(2);

        // Add an extra element to the container in the DOM
        $("<p>Not a container item!</p>").appendTo("#parent_element");

        // Expect the count to remain the same
        expect(container.getItemValues().length).toEqual(2);

        // Add another element
        container.add();
        expect(container.getItemValues().length).toEqual(3);

        // Remove the first element
        container.remove(container.getItem(0));
        expect(container.getItemValues().length).toEqual(2);
    });

    it("adds an element when the add button is pressed", function() {
        // Press the add button
        expect(container.getItemValues().length).toEqual(0);
        $("#add_button").click();
        expect(container.getItemValues().length).toEqual(1);
    });

    it("only creates one item when add is fired", function() {
        // Initialize multiple containers without explicitly adding event
        // listeners
        createContainer();
        createContainer();
        createContainer();

        // Press the add button
        expect(container.getItemValues().length).toEqual(0);
        $("#add_button").click();
        expect(container.getItemValues().length).toEqual(1);
    });

    it("removes an element when the remove button is pressed", function() {
        // Add some items
        container.add();
        container.add();
        container.add();
        expect(container.getItemValues().length).toEqual(3);

        // Press the button to delete the second item
        $(".remove_button", container.getItem(1).element).click();
        expect(container.getItemValues().length).toEqual(2);
        expect(container.getItemValues()).toEqual([
            { id: 0 },
            { id: 2 }
        ]);
    });

    it("configures remove buttons for pre-existing items", function() {
        // Add an item directly to the container element in the DOM,
        // before initializing the container object.
        $("#container").append(
            '<div class="container_item" test_id="0">' +
                '<div class="remove_button" />' +
            '<div>'
        );

        // Initialize the container object
        container = createContainer();

        // Explicitly add event listeners.
        container.addEventListeners();

        // Verify that the container recognizes the pre-existing item
        expect(container.getItemValues()).toEqual([{ id: 0 }]);

        // Expect that we can click the "remove" button
        // to remove the item.
        $(".remove_button", container.getItem(0).element).click();
        expect(container.getItemValues().length).toEqual(0);
    });
});