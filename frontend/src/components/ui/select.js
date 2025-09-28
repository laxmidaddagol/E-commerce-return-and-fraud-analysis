import React from 'react';
import { cn } from '../../lib/utils';

const SelectContext = React.createContext();

const Select = ({ value, onValueChange, children, ...props }) => {
  const [isOpen, setIsOpen] = React.useState(false);
  const [selectedValue, setSelectedValue] = React.useState(value);

  React.useEffect(() => {
    setSelectedValue(value);
  }, [value]);

  const handleValueChange = (newValue) => {
    setSelectedValue(newValue);
    onValueChange?.(newValue);
    setIsOpen(false);
  };

  return (
    <SelectContext.Provider value={{ 
      isOpen, 
      setIsOpen, 
      selectedValue, 
      handleValueChange 
    }}>
      <div className="relative" {...props}>
        {children}
      </div>
    </SelectContext.Provider>
  );
};

const SelectTrigger = React.forwardRef(({ className, children, ...props }, ref) => {
  const { isOpen, setIsOpen } = React.useContext(SelectContext);
  
  return (
    <button
      ref={ref}
      type="button"
      className={cn(
        "flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      onClick={() => setIsOpen(!isOpen)}
      {...props}
    >
      {children}
      <svg
        className={cn("h-4 w-4 opacity-50 transition-transform", isOpen && "rotate-180")}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <polyline points="6,9 12,15 18,9" />
      </svg>
    </button>
  );
});
SelectTrigger.displayName = "SelectTrigger";

const SelectValue = ({ placeholder, className, ...props }) => {
  const { selectedValue } = React.useContext(SelectContext);
  
  return (
    <span className={cn("block truncate", className)} {...props}>
      {selectedValue || placeholder}
    </span>
  );
};

const SelectContent = React.forwardRef(({ className, children, ...props }, ref) => {
  const { isOpen } = React.useContext(SelectContext);
  
  if (!isOpen) return null;
  
  return (
    <div
      ref={ref}
      className={cn(
        "absolute top-full z-50 mt-1 min-w-[8rem] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md animate-in fade-in-0 zoom-in-95",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
});
SelectContent.displayName = "SelectContent";

const SelectItem = React.forwardRef(({ className, value, children, ...props }, ref) => {
  const { selectedValue, handleValueChange } = React.useContext(SelectContext);
  
  return (
    <div
      ref={ref}
      className={cn(
        "relative flex w-full cursor-pointer select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground",
        selectedValue === value && "bg-accent text-accent-foreground",
        className
      )}
      onClick={() => handleValueChange(value)}
      {...props}
    >
      {selectedValue === value && (
        <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
            <polyline points="20,6 9,17 4,12" fill="none" stroke="currentColor" strokeWidth="2" />
          </svg>
        </span>
      )}
      {children}
    </div>
  );
});
SelectItem.displayName = "SelectItem";

export { Select, SelectContent, SelectItem, SelectTrigger, SelectValue };