#######################
0003 UI Mixins
#######################

Status
******

Accepted (September 2023)

Context
*******

Previously, ORA frontend development has been challenging. ORA frontends were built
using a combination of a placeholder Django template and injection of per-step HTML.
Additionally, the way we built the context and HTML per section mixed business and
presentation logic in complicated ways. This made refactoring and accessing that
underlying data in any other context challenging.

Along the way to creating a new ORA UI, we decided on some refactoring to aid access
to that data and allow us to reuse that code across UI implementations.

Decisions
*********

- We will create standalone APIs for accessing data on an ORA block, placed in
  ``openassessment/xblock/apis``. These APIs will be instantiated at block load and act
  as the primary way we access data / functions on the ORA block.
- We will move existing presentation code into ``openassessment/xblock/ui_mixins/legacy``,
  refactoring to leverage our newly-created APIs for data access. 
- New UI variants will also be created in ``openassessment/xblock/ui_mixins`` as separate
  folders.

Consequences
************

Separate data / utility APIs
==============================

Splitting the data / utilities out of existing mixins and into a separate location
allows us to access that data across multiple contexts, without having to duplicate
business logic.

These APIs, in addition to serving our legacy UI views, can also be leveraged in future
UI views or other contexts that need access to that data or functions.

Having those APIs and business logic in a single place will help us keep behavior from
unintentionally drifting between UIs or other endpoints.

Refactoring legacy presentation code
====================================

Refactoring our legacy presentation will allow us to leverage and exercise our APIs
ensuring behavior is not altered from before refactor to after refactor.

Moving this legacy presentation code will also allow us to decouple it from its
currently tightly-coupled location inside of the openassessment block.

Location for new UI variants
============================

Creating a specific location for UI variants (past and present) helps clearly
separate our presentation and business concerns.

Additionally, this gives us a well-defined pattern for introducing new UIs or iterating
on our UIs moving forward.
