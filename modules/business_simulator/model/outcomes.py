class Sale:
    def __init__(self, service_sold, amount, purchaser):
        self.service_sold = service_sold
        self.sold = amount
        self.purchaser = purchaser

    def __repr__(self):
        return "Sold " + str(self.sold) + " units of " + self.service_sold + " to customer type: " + self.purchaser

    def __str__(self):
        return "Sold " + str(self.sold) + " units of " + self.service_sold + " to customer type: " + self.purchaser