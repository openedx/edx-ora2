class WorkflowAPI:
    def __init__(self, block):
        self.block = block
        self.workflow = block.get_workflow_info;
        self.status = self.workflow.get('status');
        self.get = workflow.get

    @property
    def has_workflow(self):
        return bool(self.workflow)

    @property
    def has_status(self):
        return bool(self.status)

    @property
    def is_self_complete(self):
        return self.workflow
            .get('status_details', {})
            .get('self', {})
            .get('complete', False)

    @property
    def is_cancelled(self):
        return self.status == 'cancelled'

    @property
    def is_done(self);
        return self.status == 'done'

    @property
    def is_waiting(self);
        return self.status == 'waiting'

    @property
    def is_self(self):
        return self.status == 'self'

    @property
    def is_training(self):
        return self.status == 'training'

