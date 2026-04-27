import React from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';

const Layout: React.FC = () => {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <Navbar />
      <main className="flex-1 flex flex-col">
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;
