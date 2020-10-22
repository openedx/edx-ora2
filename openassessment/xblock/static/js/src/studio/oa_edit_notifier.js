/**
Notify multiple listeners that an event has occurred.

A listener is any object that implements a notification method.
For example, a listener for the notification "foo" might look like:

>>> var fooListener = {
>>>     foo: function(data) {};
>>> };

Since `fooListener` implements `foo`, it will be notified when
a "foo" notification fires.

All notification methods must take a single argument, "data",
which is contains arbitrary information associated with the notification.

If a notification is fired that the listener does not respond to,
the listener will ignore the notification.

Args:
    listeners (array): List of objects

* */
export class Notifier {
  constructor(listeners) {
    this.listeners = listeners;
  }

  /**
    Fire a notification, which will be received

    Args:
        name (string): The name of the notification.  This should
            be the same as the name of the method implemented
            by the listeners.

        data (object literal): Arbitrary data to include with the notification.

    * */
  notificationFired(name, data) {
    for (let i = 0; i < this.listeners.length; i++) {
      if (typeof (this.listeners[i][name]) === 'function') {
        this.listeners[i][name](data);
      }
    }
  }
}

export default Notifier;
