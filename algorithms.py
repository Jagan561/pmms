class PredictiveAllocator:
    def __init__(self, os_layer, predictor):
        self.os_layer = os_layer
        self.predictor = predictor

    def allocate(self, time, prediction):
        process_id = f"P{time}"
        self.os_layer.allocate(process_id, prediction)
        return process_id
